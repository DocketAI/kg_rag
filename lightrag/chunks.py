import json
import boto3
import psycopg2
from collections import Counter
from functools import lru_cache
from .base import TextChunkSchema
from .utils import encode_string_by_tiktoken, merge_content
from .prompt import AGG_CHUNK_SEP
from .config import (
    config_file,
    chunks_table,
    subgraph_sources,
)


def get_file(file, env):
    file = file.format(env)
    s3_bucket = file.split("/")[2]
    prefix = "/".join(file.split("/")[3:])
    return s3_bucket, prefix

@lru_cache(maxsize=128)
def read_config(file, env):
    s3_bucket, prefix = get_file(file, env)
    s3 = boto3.resource("s3")
    content_object = s3.Object(s3_bucket, prefix)
    file_content = content_object.get()["Body"].read().decode("utf-8")
    return file_content

def db_connection(env):
    creds = read_config(config_file, env)
    creds = json.loads(creds)
    rds_client = boto3.client("rds")
    auth_token = rds_client.generate_db_auth_token(
        DBHostname=creds["host"],
        Port=creds["port"],
        DBUsername=creds["user"],
        Region=creds["region"],
    )
    return psycopg2.connect(
        user=creds["user"],
        password=auth_token,
        host=creds["host"],
        port=creds["port"],
        database=creds["db"],
        sslmode="require",
    )


async def get_docs(company_id: int, env: str):
    connection = None
    docs = []
    try:
        connection = db_connection(env)
        cursor = connection.cursor()
        docs_query = f"SELECT DISTINCT source_id FROM {chunks_table} WHERE company_id = {company_id}"
        cursor.execute(docs_query)
        docs = [doc[0] for doc in cursor.fetchall()]
        print(f"Total {len(docs)} docs found")
    except Exception as e:
        print("Error occurred:", e)
    finally:
        if connection:
            connection.close()
    return docs


def get_unique_chunk_ids(chunk_ids):
    chunk_ids_split = [cid.split('-') for cid in chunk_ids]
    chunk_ids_freq = Counter(item[1] for item in chunk_ids_split)
    min_freq_chunk_id = min(chunk_ids_freq, key=chunk_ids_freq.get)
    return [i for i, item in enumerate(chunk_ids_split) if item[1] == min_freq_chunk_id]


async def get_chunks(doc_id: int, min_tokens, company_id: int, env: str):
    connection = None
    chunks = []
    try:
        connection = db_connection(env)
        cursor = connection.cursor()
        docs_query = f"""
            SELECT chunk_id, content, sequence, source
            FROM {chunks_table} WHERE company_id = {company_id} AND source_id = {doc_id}
            ORDER BY sequence"""
        cursor.execute(docs_query)
        rows = cursor.fetchall()
        chunks = [rows[row_idx] for row_idx in get_unique_chunk_ids([row[0] for row in rows])]
    except Exception as e:
        print("Error occurred:", e)
    finally:
        if connection:
            connection.close()
    return get_chunks_helper(chunks, min_tokens, doc_id)


def get_chunks_helper(rows, min_tokens: int, source_id: int):
    combined_chunks = []

    current_chunk_ids = []
    current_contents = []
    current_tokens = 0
    combined_sequence = 0

    for chunk_id, content, sequence, source in rows:
        tokens = len(encode_string_by_tiktoken(content))
        current_chunk_ids.append(chunk_id)
        current_contents.append(content)
        current_tokens += tokens

        if current_tokens >= min_tokens:
            combined_chunk_id = AGG_CHUNK_SEP.join(current_chunk_ids)
            combined_chunks.append({
                "tokens": current_tokens,
                "chunk_id": combined_chunk_id,
                "content": merge_content(current_contents),
                "sequence": combined_sequence,
                "source_id": source_id,
                "subgraphs": subgraph_sources.get(source, []) + ['ALL'],
            })
            
            combined_sequence += 1
            current_chunk_ids = []
            current_contents = []
            current_tokens = 0

    if current_tokens > 0:
        combined_chunk_id = AGG_CHUNK_SEP.join(current_chunk_ids)
        combined_chunks.append({
            "tokens": current_tokens,
            "chunk_id": combined_chunk_id,
            "content": merge_content(current_contents),
            "sequence": combined_sequence,
            "source_id": source_id,
            "subgraphs": subgraph_sources.get(source, []) + ['ALL'],
        })
        
    return {
        ch["chunk_id"]: TextChunkSchema(
            tokens=ch["tokens"],
            content=ch["content"],
            full_doc_id=str(ch["source_id"]),
            chunk_order_index=ch["sequence"],
            subgraphs=ch["subgraphs"]
        )
        for ch in combined_chunks
    }


async def main():
    await get_chunks(
        min_tokens=1200,
        batch_size=100,
        company_id=18,
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
