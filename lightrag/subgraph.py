import os
import json
from enum import Enum
from firecrawl import FirecrawlApp
from .prompt import PROMPTS
from lightrag.subgraphs import pkg_schema
from subgraph_neo4j_visualisation import load_data_to_neo4j

app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])

class Subgraph(str, Enum):
    PKG = "pkg"

graph_schema_mapping = {
    Subgraph.PKG.value: pkg_schema
}

def create_subgraph(subgraph: Subgraph, url: str):
    data = app.extract([
    url
    ], {
        "prompt": PROMPTS["firecrawl_prompt_pkg"],
        "schema": graph_schema_mapping[subgraph.value]
    })
    print(f"Loading data into neo4j")
    with open("firecrawl_results.json", "w") as f:
        json.dump(data["data"], f)
    load_data_to_neo4j(data["data"])