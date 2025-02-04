import json

with open("lightrag/subgraphs/schemas/pkg.json", "r") as f:
    pkg_schema = json.load(f)

__all__ = ["pkg_schema"]