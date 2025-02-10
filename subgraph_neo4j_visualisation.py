import os
import json
from neo4j import GraphDatabase

def load_data_to_neo4j(data):
    uri = os.environ["NEO4J_URI"]
    user = os.environ["NEO4J_USERNAME"]
    password = os.environ["NEO4J_PASSWORD"]
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        
        # 1. Create unique constraints (so we don't get duplicates on MERGE)
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (pl:PRODUCT_LINE) REQUIRE pl.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (ps:PRODUCT_SKU) REQUIRE ps.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:FEATURE) REQUIRE f.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (sc:SECURITY) REQUIRE sc.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (sme:SME) REQUIRE sme.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (uc:USE_CASE) REQUIRE uc.name IS UNIQUE")
        
        # 2. Insert nodes for each array in the JSON
        
        # product_lines
        for pl in data.get("PRODUCT_LINE", []):
            session.run(
                """
                MERGE (p:PRODUCT_LINE {name: $name})
                SET p.description = $description
                """,
                {"name": pl["name"], "description": pl.get("description", "")}
            )
        
        # product_skus
        for sku in data.get("PRODUCT_SKU", []):
            session.run(
                """
                MERGE (s:PRODUCT_SKU {name: $name})
                SET s.description = $description
                """,
                {"name": sku["name"], "description": sku.get("description", "")}
            )
        
        # features
        for feat in data.get("FEATURE", []):
            session.run(
                """
                MERGE (f:FEATURE {name: $name})
                SET f.description = $description
                """,
                {"name": feat["name"], "description": feat.get("description", "")}
            )
        
        # security
        for sec in data.get("SECURITY", []):
            session.run(
                """
                MERGE (sc:SECURITY {name: $name})
                SET sc.description = $description
                """,
                {"name": sec["name"], "description": sec.get("description", "")}
            )
        
        # smes
        for sme in data.get("SME", []):
            session.run(
                """
                MERGE (sme:SME {name: $name})
                SET sme.description = $description
                """,
                {"name": sme["name"], "description": sme["description"]}
            )
        
        # use_cases
        for uc in data.get("USE_CASE", []):
            session.run(
                """
                MERGE (u:USE_CASE {name: $name})
                SET u.description = $description
                """,
                {"name": uc["name"], "description": uc.get("description", "")}
            )
        
        # 3. Insert relationships
        for rel in data.get("RELATIONS", []):
            src_label = rel["source_type"]
            source_name = rel["source_name"]
            tgt_label = rel["target_type"]
            target_name = rel["target_name"]
            rel_type = rel["relationship_type"]
            
            if (not src_label) or (not tgt_label) or (not rel_type):
                print(f"Skipping adding relation, one of src_label: {src_label}, tgt_label: {tgt_label}, rel_type: {rel_type} is none")
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
        
        session.run(
            """
            MATCH (n:SME)
            SET n.name = n.name + " - " + n.description
            RETURN n
            """
        )
    
    driver.close()

if __name__ == "__main__":
    with open("firecrawl_results.json", "r") as f:
        data = json.load(f)
    print(f"Ingesting entity types - {', '.join(data.keys())}")
    load_data_to_neo4j(data)
    print("Data loaded into Neo4j.")
