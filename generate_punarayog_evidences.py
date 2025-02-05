import os, json, requests, time
import pandas as pd
from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_mini_complete
import uuid  

WORKING_DIR = "./artifacts"




if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)

rag = LightRAG(
    working_dir=WORKING_DIR,
    llm_model_func=gpt_4o_mini_complete,  # Use gpt_4o_mini_complete LLM model
    # llm_model_func=gpt_4o_complete  # Optionally, use a stronger model
)

with open("./artifacts/pg_0.txt", "r", encoding="utf-8") as f:
    rag.insert(f.read())




# Load questions from CSV and create a dictionary
pkg_raw_df = pd.read_csv("pkg_100_questions.csv")
pkg_questions_dict = pkg_raw_df.set_index("id")["query"].to_dict()

# Initialize an empty DataFrame for storing evidence
columns = ["query", "id", "text", "relevance", "quality_assessment", "source", "chunks"]
df = pd.DataFrame(columns=columns)

# Output directory setup
output_dir = "evaluation_output/"
count = 0

for id, query in pkg_questions_dict.items():
    try:
        # Call the punarayog api
        url = "http://punarayog.internal.app.docketai.com/metaretriever"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        data = {
            "transaction_id": f"lightrag-query-{count}-{str(uuid.uuid4())[:4]}", 
            "limit": 15,
            "question": query,
            "company_id": 18
        }

        eval_api_response = requests.post(url, headers=headers, json=data)
        print("Status Code:", eval_api_response.status_code)

        if eval_api_response.status_code == 200:
            punarayog_response_data = eval_api_response.json()
            chunk_contents = [chunk.get("content", "") for chunk in punarayog_response_data.get("chunks", [])]
            chunks_context = "\n\n".join(chunk_contents)

                    
        # Call the evidence extraction API
        url = "http://127.0.0.1:8080/extract_evidence/"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        data = {
            "query": query,
            "chunks": chunks_context
        }

        eval_api_response = requests.post(url, headers=headers, json=data)
        print("Status Code:", eval_api_response.status_code)

        if eval_api_response.status_code == 200:
            # Parse API response and update DataFrame
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
                        "source": "punarayog",
                        "chunks": chunks_context
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        else:
            print(f"API call failed for query ID {id}: {eval_api_response.status_code}")

        # Stop after 5 queries
        count += 1
        # if count == :
        #     break
        time.sleep(5)
        print(f"Processed {count} cases.")


    except Exception as e:
        print(f"Error processing query ID {id}: {e}")

# Print the updated DataFrame
df.to_csv(f"Response_Punarayog.csv", index=False)