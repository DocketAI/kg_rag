import os, json, requests, time, re
import pandas as pd
from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_mini_complete

WORKING_DIR = "./artifacts"

if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)

# Load questions from CSV and create a dictionary
pkg_raw_df = pd.read_csv("pkg_100_questions.csv")
pkg_questions_dict = pkg_raw_df.set_index("id")["query"].to_dict()

# Initialize an empty DataFrame for storing evidence
columns = ["query", "id", "text", "relevance", "quality_assessment", "source", "chunks"]
df = pd.DataFrame(columns=columns)

# Assuem id, query, kg_context is coming from csv
light_rag_dict = pd.read_csv("context_separated.csv").set_index('id')[['query', 'chunks_context', 'entities_context', 'relations_context']].to_dict(orient='index')


count = 0

for id, row in pkg_questions_dict.items():
    try:
        query = light_rag_dict.get(id).get('query')
        # chunks_context_dict = extract_sections(light_rag_dict.get(id).get('chunks_context')) #if going for multiple entity type

        chunks_context_dict = {
            "entities": light_rag_dict.get(id).get('entities_context'),
            "relationships": light_rag_dict.get(id).get('relations_context'),
            "sources": light_rag_dict.get(id).get('chunks_context')
        }
                            
        # Call the evidence extraction API
        url = "http://127.0.0.1:8080/extract_evidence/"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        data = {
            "query": query,
            # "chunks": chunks_context_dict.get('sources') # Add entities_context or relations_context if going for multiple entity type
            "chunks": f"--EntitiesContext--\n{chunks_context_dict.get('entities')}\n\n--RelationsContext--\n{chunks_context_dict.get('relationships')}\n\n--Sources--\n{chunks_context_dict.get('sources')}"
        }

        eval_api_response = requests.post(url, headers=headers, json=data)
        print("Status Code:", eval_api_response.status_code)

        if eval_api_response.status_code == 200:
            eval_data = eval_api_response.json()

            if "error" not in eval_data.keys():
                evidences = eval_data.get("evidences", [])
                for evidence in evidences:
                    new_row = {
                        "query": query,
                        "id": evidence.get("id"),
                        "text": evidence.get("text"),
                        "relevance": evidence.get("relevance"),
                        "quality_assessment": evidence.get("quality_assessment"),
                        "source": "LightRAG",
                        "chunks": evidence.get("chunks")
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        else:
            print(f"API call failed for query ID {id}: {eval_api_response.status_code}")

        count += 1
        time.sleep(2)
        print(f"Processed {count} cases.")


    except Exception as e:
        print(f"Error processing query ID {id}: {e}")

# Print the updated DataFrame
df.to_csv(f"Response_LightRAG_sources.csv", index=False)