import os
import json
from enum import Enum
from functools import partial
from firecrawl import FirecrawlApp
from .prompt import PROMPTS
from lightrag.subgraphs import pkg_schema
from lightrag.config import max_glean_steps
from subgraph_neo4j_visualisation import load_data_to_neo4j

app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])

class Subgraph(str, Enum):
    PKG = "pkg"

graph_schema_mapping = {
    Subgraph.PKG.value: pkg_schema
}

def extract(subgraph: Subgraph, url: str):
    data = app.extract([
    url
    ], {
        "prompt": PROMPTS["firecrawl_prompt_pkg"],
        "schema": graph_schema_mapping[subgraph.value],
        "enableWebSearch": True
    })
    return data

def update_master(master_copy, update_copy):
    for key in update_copy:
        if key not in master_copy:
            master_copy[key] = update_copy[key]
        else:
            master_copy[key].extend(update_copy[key])
    return master_copy

def create_subgraph(subgraph: Subgraph, url: str):
    master_data = {}
    extract_caller = partial(extract, subgraph=subgraph, url=url)
    for i in range(max_glean_steps):
        print(f"Extracting {i+1} of {max_glean_steps} times...")
        new_data = extract_caller()
        master_data = update_master(master_data, new_data["data"])
    
    with open("firecrawl_results_raw.json", "w") as f:
        json.dump(master_data, f)
    # load_data_to_neo4j(master_data)