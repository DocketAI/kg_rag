from typing import List, Dict
import json, re
# from openai import OpenAI
import openai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
import os


import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# FastAPI app
app = FastAPI()

# Load environment variables
load_dotenv()

# Set OpenAI API Key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Evidence extraction prompt
EVIDENCE_EXTRACTION_PROMPT = """
You are an evidence extraction system analyzing content specific to B2B SaaS (Business-to-Business Software as a Service) products.
An evidence is a factually verifiable sentence, which has overlapping keyword potential, named entities present, and rich textual information.

## Objective:
Your task is to identify and extract the maximum number of sentences that can serve as verifiable evidence for the given query. 
These sentences should help support reasoning and connecting information from multiple sources to answer the query effectively. 
You MUST not edit or modify the extracted sentence.

## Extraction Criteria:
1. Factually Verifiable: The sentence must contain specific facts, statistics, or well-supported opinions.
2. Keyword Overlap Potential: Includes keywords likely to overlap with the query and other content, enabling connections across documents.
3. Named Entities Present: Mentions specific entities such as people, organizations, products, or locations that can be relevant to the query.
4. Detailed and Specific: Contains precise details, such as numbers, dates, events, definitions, or comparisons, that add value and context around the query.

## Evaluation Metrics for Extracted Evidence:

a. Relevance:
Evaluates how closely the context of the sentence aligns with the given query.
High relevance: Context is directly tied to the query's intent and provides essential information.
Medium relevance: Context partially overlaps with the query but lacks direct focus.
Low relevance: Context is loosely related or tangential to the query.

b. Quality Assessment (Quality Evidence):
Assesses the richness and informativeness of the evidence.
Good quality: Sentence includes detailed, precise information (e.g., numbers, statistics, named entities) that adds depth to reasoning.
Average quality: Sentence provides moderately useful information but lacks depth or specificity.
Poor quality: Sentence lacks useful details or contains general, vague content.

## Rejection Criteria:
1. Marketing Language: Avoid phrases like "revolutionary" or "cutting-edge."
2. Generalizations: Exclude vague or generic statements.
3. Lack of Specificity: Discard sentences that do not offer precise, actionable information.
4. Questions: Discard sentences that are direct questions.

## Expected Output:
- Extracted evidences in JSON format.
- Each evidence should be tagged with its relevance and quality assessment.
"""


class EvidenceRequest(BaseModel):
    query: str
    chunks: str

class CompareEvidenceRequest(BaseModel):
    query: str
    punarayog_evidences: List[str]
    lightrag_evidences: List[str]

def compare_evidence(query: str, punarayog_evidences: List[str], light_rag_evidences: List[str]) -> Dict:
    try:
        json_template = {
            "query": query,
            "common_evidences": [
                {
                    "text": "evidence text that appears in both systems",
                    "punarayog_metadata": {
                        "relevance": "High/Medium/Low",
                        "quality_assessment": "Good/Average/Poor"
                    },
                    "lightrag_metadata": {
                        "relevance": "High/Medium/Low",
                        "quality_assessment": "Good/Average/Poor"
                    }
                }
            ],
            "unique_lightrag_evidences": [
                {
                    "text": "evidence text unique to lightrag",
                    "relevance": "High/Medium/Low",
                    "quality_assessment": "Good/Average/Poor"
                }
            ],
            "unique_punarayog_evidences": [
                {
                    "text": "evidence text unique to punarayog",
                    "relevance": "High/Medium/Low",
                    "quality_assessment": "Good/Average/Poor"
                }
            ]
        }

        prompt = f"""
            Query: {query}

            To answer this given query, we have evidences from two different systems (Punarayog and LightRAG). You need to analyze these evidences and their overlap and unique contributions.
            
            Task:
            1. Read and understand the evidences that are present in both systems and has similar information in it. 
            2. Identify information in evidences uniquely coming from LightRAG and are not present in Punarayog.
            3. Identify information in evidences uniquely coming from Punarayog and are not present in LightRAG.
            
            For matching evidences, consider similarity of information in them rather than exact matches.
            Include the relevance and quality assessment from each system where applicable.

            Punarayog Evidences:
            {punarayog_evidences}

            LightRAG Evidences:
            {light_rag_evidences}

            Expected Output Format:
            {json.dumps(json_template, indent=2)}
        """

        # Make the LLM call
        response = openai.ChatCompletion.create(
            model="o1-mini",
            # temperature=0.0,
            max_completion_tokens=8192,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract content from the response
        response_content = response['choices'][0]['message']['content']
        response_content = response_content.replace("\n", "")
        
        try:
            match = re.search(r"\{.*\}", response_content, re.DOTALL)
            if match:
                response_content = match.group(0)
                comparison_result = json.loads(response_content)
                logger.info(f"Successfully compared evidences from both systems")
            else:
                logger.error("No correct JSON-like structure found in the result.")
                return {"error": "Invalid response format"}

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return {"error": "Failed to parse comparison results"}

        return comparison_result

    except Exception as e:
        logger.error(f"Error during evidence comparison: {e}")
        return {"error": str(e)}
    
    

# Evidence extraction function
def extract_evidence(query: str, combined_content: str) -> Dict:
    try:
        json_template = {
            "query": query,
            "evidences": [
                {
                    "id": "auto increment integer",
                    "text": "extracted sentence from input content",
                    "relevance": "High/Medium/Low",
                    "quality_assessment": "Good/Average/Poor"
                }
            ]
        }

        prompt = f"""
            Query: {query}

            Please extract evidences from the following B2B SaaS content based on the query.
            Each extracted evidence should be relevant to the query and formatted as specified below.
            Assess the relevance (High/Medium/Low) and quality (Good/Average/Poor) of each evidence.

            Input Content:\n
            {combined_content}

            Expected Output Format:\n
            {json.dumps(json_template, indent=2)}
        """

        # Make the LLM call without streaming to debug
        response = openai.ChatCompletion.create(
            model="gpt-4o",  
            temperature=0.0,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract content from the response
        response_content = response['choices'][0]['message']['content']
        response_content = response_content.replace("\n","")
        try:
        # json_text = locate_json_string_body_from_string(result) # handled in use_model_func
            match = re.search(r"\{.*\}", response_content, re.DOTALL)
            if match:
                response_content = match.group(0)
                llm_result = json.loads(response_content)

                query = llm_result.get("query", [])
                evidences = llm_result.get("evidences", [])
                print(f"Length of Evidences is {len(evidences)}")
            else:
                logger.error("No Correct JSON-like structure found in the result.")
                query=query
                evidences=[]

        # Handle parsing error
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e} {response_content}")
            return None

        # Parse and return the JSON response
        return json.loads(response_content)

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return {"error": "Invalid JSON in API response"}
    except Exception as e:
        print(f"Error during evidence extraction LLM call: {e}")
        return {"error": str(e)}

# FastAPI endpoint
@app.post("/extract_evidence/")
def extract_evidence_endpoint(request: EvidenceRequest):
    logger.info(f"Running API..")
    try:
        query = request.query
        evidence_response = extract_evidence(query, request.chunks)
        return evidence_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
@app.post("/compare_evidence/")
def compare_evidence_endpoint(request: CompareEvidenceRequest):
    try:
        query = request.query
        evidence_response = compare_evidence(query, request.punarayog_evidences, request.lightrag_evidences)
        return evidence_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Run with `uvicorn`:
if __name__ == "__main__":
    # request = EvidenceRequest(query="what did ZoomInfo start?",
    #                           chunks="ZoomInfo started in 2022\n\n\nZoominfo was started in Delmonte, USA")
    # extract_evidence_endpoint(request)
    # request = CompareEvidenceRequest(query="what did ZoomInfo start?",
    #                           punarayog_evidences=["ZoomInfo started in 2022"],
    #                           lightrag_evidences=["ZoomInfo was found around 2022", "Zoominfo was started in Delmonte, USA"])
    # response = compare_evidence_endpoint(request)
    # print(response)

    uvicorn.run("evaluate_api:app", port=8080, log_level="info")
