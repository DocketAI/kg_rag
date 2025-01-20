import os
from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_mini_complete
#########
# Uncomment the below two lines if running in a jupyter notebook to handle the async nature of rag.insert()
# import nest_asyncio
# nest_asyncio.apply()
#########

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

# Perform naive search
# print(
#     rag.query("What are the comments of Mike Clum about the products of ZoomInfo?", param=QueryParam(mode="naive"))
# )

# # Perform local search
# print(
#     rag.query("What are the comments of Mike Clum about the products of ZoomInfo?", param=QueryParam(mode="local"))
# )

# Perform global search
print(
    rag.query("List down the top features and their use cases about ZoomInfo Copilot?", param=QueryParam(mode="global"))
)

# Perform hybrid search
print(
    rag.query("What are the product lines of ZoomInfo?", param=QueryParam(mode="hybrid"))
)
