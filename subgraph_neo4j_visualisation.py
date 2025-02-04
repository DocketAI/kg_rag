import os
import json
from neo4j import GraphDatabase

def load_data_to_neo4j(data):
    node_label_map = {
        "product_line": "ProductLine",
        "product_sku": "ProductSKU",
        "feature": "Feature",
        "security": "Security",
        "sme": "SME",
        "use_case": "UseCase"
    }
    
    # Map relationship_type to a Cypher-friendly relationship name
    rel_type_map = {
        "has_product_sku": "HAS_PRODUCT_SKU",
        "has_feature": "HAS_FEATURE",
        "has_use_case": "HAS_USE_CASE",
        "has_sme": "HAS_SME",
        "has_security": "HAS_SECURITY"
    }

    uri = os.environ["NEO4J_URI"]
    user = os.environ["NEO4J_USERNAME"]
    password = os.environ["NEO4J_PASSWORD"]
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        
        # 1. Create unique constraints (so we don't get duplicates on MERGE)
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (pl:ProductLine) REQUIRE pl.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (ps:ProductSKU) REQUIRE ps.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:Feature) REQUIRE f.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (sc:Security) REQUIRE sc.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (sme:SME) REQUIRE sme.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (uc:UseCase) REQUIRE uc.name IS UNIQUE")
        
        # 2. Insert nodes for each array in the JSON
        
        # product_lines
        for pl in data.get("product_lines", []):
            session.run(
                """
                MERGE (p:ProductLine {name: $name})
                SET p.description = $description
                """,
                {"name": pl["product_line_name"], "description": pl.get("description", "")}
            )
        
        # product_skus
        for sku in data.get("product_skus", []):
            session.run(
                """
                MERGE (s:ProductSKU {name: $name})
                SET s.description = $description
                """,
                {"name": sku["product_sku_name"], "description": sku.get("description", "")}
            )
        
        # features
        for feat in data.get("features", []):
            session.run(
                """
                MERGE (f:Feature {name: $name})
                SET f.description = $description
                """,
                {"name": feat["feature_name"], "description": feat.get("description", "")}
            )
        
        # security
        for sec in data.get("security", []):
            session.run(
                """
                MERGE (sc:Security {name: $name})
                SET sc.description = $description
                """,
                {"name": sec["security_name"], "description": sec.get("description", "")}
            )
        
        # smes
        for sme in data.get("smes", []):
            session.run(
                """
                MERGE (sme:SME {name: $name})
                SET sme.role = $role
                """,
                {"name": sme["sme_name"], "role": sme["role"]}
            )
        
        # use_cases
        for uc in data.get("use_cases", []):
            session.run(
                """
                MERGE (u:UseCase {name: $name})
                SET u.description = $description
                """,
                {"name": uc["use_case_name"], "description": uc.get("description", "")}
            )
        
        # 3. Insert relationships
        for rel in data.get("relationships", []):
            source_type = rel["source_type"]
            source_name = rel["source_name"]
            target_type = rel["target_type"]
            target_name = rel["target_name"]
            relationship_type = rel["relationship_type"]
            
            src_label = node_label_map.get(source_type, None)
            tgt_label = node_label_map.get(target_type, None)
            rel_type = rel_type_map.get(relationship_type, None)
            if (not src_label) or (not tgt_label) or (not rel_type):
                print(f"Skipping adding relation, one of src_label: {source_type}, tgt_label: {target_type}, rel_type: {relationship_type} is none")
                continue
            
            # Create the relationship
            session.run(
                f"""
                MATCH (src:{src_label} {{name: $src_name}})
                MATCH (tgt:{tgt_label} {{name: $tgt_name}})
                MERGE (src)-[r:{rel_type}]->(tgt)
                """,
                {"src_name": source_name, "tgt_name": target_name}
            )
    
    driver.close()

if __name__ == "__main__":
    with open("firecrawl_results.json", "r") as f:
        data = json.load(f)
    data = data[0]
    print(f"Ingesting entity types - {', '.join(data.keys())}")
    load_data_to_neo4j(data)
    print("Data loaded into Neo4j.")
