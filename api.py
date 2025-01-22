from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
import os
from lightrag import LightRAG, QueryParam
from lightrag.llm import openai_complete_if_cache, openai_embedding
from lightrag.utils import EmbeddingFunc, save_or_load_known_entities
from lightrag.config import insert_batch_size, min_chunk_tokens, env
from dotenv import load_dotenv
import numpy as np
from typing import Optional, Dict, Any
from enum import Enum
import asyncio
import nest_asyncio

load_dotenv()
# Apply nest_asyncio to solve event loop issues
nest_asyncio.apply()

DEFAULT_RAG_DIR = "index_default"
app = FastAPI(title="LightRAG API", description="API for RAG operations")

# Configure working directory
WORKING_DIR = os.environ.get("RAG_DIR", f"{DEFAULT_RAG_DIR}")
print(f"WORKING_DIR: {WORKING_DIR}")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
print(f"LLM_MODEL: {LLM_MODEL}")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")
print(f"EMBEDDING_MODEL: {EMBEDDING_MODEL}")
EMBEDDING_MAX_TOKEN_SIZE = int(os.environ.get("EMBEDDING_MAX_TOKEN_SIZE", 8192))
print(f"EMBEDDING_MAX_TOKEN_SIZE: {EMBEDDING_MAX_TOKEN_SIZE}")

if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)


# LLM model function


async def llm_model_func(
    prompt, system_prompt=None, history_messages=[], keyword_extraction=False, **kwargs
) -> str:
    return await openai_complete_if_cache(
        LLM_MODEL,
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        **kwargs,
    )


# Embedding function


async def embedding_func(texts: list[str]) -> np.ndarray:
    return await openai_embedding(
        texts,
        model=EMBEDDING_MODEL,
    )


async def get_embedding_dim():
    test_text = ["This is a test sentence."]
    embedding = await embedding_func(test_text)
    embedding_dim = embedding.shape[1]
    print(f"{embedding_dim=}")
    return embedding_dim


# Initialize RAG instance
rag = LightRAG(
    working_dir=WORKING_DIR,
    addon_params={
        "env": env,
        "insert_batch_size": insert_batch_size,
        "min_chunk_tokens": min_chunk_tokens,
        "known_entities": save_or_load_known_entities(format=True)
    },
    llm_model_func=llm_model_func,
    embedding_func=EmbeddingFunc(
        embedding_dim=asyncio.run(get_embedding_dim()),
        max_token_size=EMBEDDING_MAX_TOKEN_SIZE,
        func=embedding_func,
    ),
)


# Data models


class QueryRequest(BaseModel):
    query: str
    mode: str = "hybrid"
    only_need_context: bool = False


class InsertRequest(BaseModel):
    text: str


class Response(BaseModel):
    status: str
    data: Optional[str] = None
    message: Optional[str] = None


class EntityType(str, Enum):
    PRODUCT_LINE = "product_line"
    PRODUCT_SKU = "product_sku"
    FEATURE = "feature"
    SECURITY = "security"
    SME = "sme"
    USE_CASE = "use_case"


class ProductLine(BaseModel):
    entity_name: str
    abbreviations: Optional[list[str]] = None
    synonyms: Optional[list[str]] = []
    partial_description: Optional[str] = None


class Feature(BaseModel):
    product_line: str
    entity_name: str
    partial_description: Optional[str] = None
    abbreviations: Optional[list[str]] = None
    synonyms: Optional[list[str]] = None


class Security(BaseModel):
    certification_name: str
    entity_name: str
    partial_description: Optional[str]
    abbreviations: Optional[list[str]]
    synonyms: Optional[list[str]]


model_mapping = {
    EntityType.PRODUCT_LINE: ProductLine,
    EntityType.FEATURE: Feature,
    EntityType.SECURITY: Security
}

# API routes


@app.post("/query", response_model=Response)
async def query_endpoint(request: QueryRequest):
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: rag.query(
                request.query,
                param=QueryParam(
                    mode=request.mode, only_need_context=request.only_need_context
                ),
            ),
        )
        return Response(status="success", data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/insert", response_model=Response)
async def insert_endpoint(request: InsertRequest):
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: rag.insert(request.text))
        return Response(status="success", message="Text inserted successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/insert_file", response_model=Response)
async def insert_file(file: UploadFile = File(...)):
    try:
        file_content = await file.read()
        # Read file content
        try:
            content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            # If UTF-8 decoding fails, try other encodings
            content = file_content.decode("gbk")
        # Insert file content
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: rag.insert(content))

        return Response(
            status="success",
            message=f"File content from {file.filename} inserted successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/insert_chunks", response_model=Response)
async def insert_chunks(company_id: int):
    try:
        rag.addon_params.update({"company_id": company_id})
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: rag.insert())

        return Response(
            status="success",
            message=f"Chunks inserted successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/add_known_entity/{entity_type}")
async def add_known_entity(entity_type: EntityType, entity_data: Dict[str, Any]):
    """
    Endpoint to add an entity of a specific type (e.g., product_line, feature).
    - entity_type: path parameter, must be one of the EntityType enum values
    - entity_data: JSON body, which we'll parse with the correct Pydantic model
    """
    model_class = model_mapping.get(entity_type)
    if not model_class:
        raise HTTPException(status_code=400, detail="Invalid or unsupported entity type")

    try:
        entity_instance = model_class(**entity_data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    save_or_load_known_entities(
        entity_type=entity_type, 
        entity_data=entity_instance.model_dump()
    )
    return {
        "message": f"Entity of type '{entity_type.value}' added successfully.",
    }



@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8020)
