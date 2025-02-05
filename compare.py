import pandas as pd
import numpy as np
from scipy.stats import mannwhitneyu
import requests
import json

def load_data():
    """Load the datasets"""
    df_punarayog = pd.read_csv("Response_Punarayog.csv")
    df_lightrag = pd.read_csv("Response_LightRAG_sources.csv")
    
    print(f"Punarayog unique queries: {df_punarayog['query'].nunique()}")
    print(f"LightRAG unique queries: {df_lightrag['query'].nunique()}")
    
    # Find intersecting queries
    common_queries = df_lightrag[df_lightrag['query'].isin(df_punarayog['query'])]
    print(f"Common queries: {common_queries['query'].nunique()}")
    
    return df_punarayog, df_lightrag

def cliffs_delta(x, y):
    """Calculate Cliff's Delta statistic"""
    if len(x) == 0 or len(y) == 0:
        return 0
    n1, n2 = len(x), len(y)
    dominance = sum(1 for xi in x for yi in y if xi > yi) - sum(1 for xi in x for yi in y if xi < yi)
    return dominance / (n1 * n2)

def evaluate_data_at_query_level(df1, df2, source1_name="lightrag", source2_name="punarayog"):
    """Evaluate data at query level with statistical measures"""
    # Rename columns for clarity
    df1 = df1.rename(columns={
        "relevance": f"relevance_{source1_name}", 
        "quality_assessment": f"quality_assessment_{source1_name}"
    })
    df2 = df2.rename(columns={
        "relevance": f"relevance_{source2_name}", 
        "quality_assessment": f"quality_assessment_{source2_name}"
    })

    merged_df = pd.merge(df1, df2, on="query", how="outer", suffixes=("_left", "_right"))
    
    metrics = []
    for query, group in merged_df.groupby("query"):
        group1 = group[[col for col in group.columns if col.endswith(f"_{source1_name}")]].dropna(how="all")
        group2 = group[[col for col in group.columns if col.endswith(f"_{source2_name}")]].dropna(how="all")

        relevance_map = {"High": 3, "Medium": 2, "Low": 1}
        quality_map = {"Good": 3, "Average": 2, "Poor": 1}

        # Convert categorical to numeric scores
        relevance_scores_1 = group1[f"relevance_{source1_name}"].map(relevance_map).tolist()
        quality_scores_1 = group1[f"quality_assessment_{source1_name}"].map(quality_map).tolist()
        relevance_scores_2 = group2[f"relevance_{source2_name}"].map(relevance_map).tolist()
        quality_scores_2 = group2[f"quality_assessment_{source2_name}"].map(quality_map).tolist()

        # Calculate metrics
        relevant_evidence_1 = (group1[f"relevance_{source1_name}"] == "High").sum()
        quality_evidence_1 = (group1[f"quality_assessment_{source1_name}"] == "Good").sum()
        relevant_evidence_2 = (group2[f"relevance_{source2_name}"] == "High").sum()
        quality_evidence_2 = (group2[f"quality_assessment_{source2_name}"] == "Good").sum()

        # Calculate medians instead of Cliff's Delta
        relevance_median_1 = np.median(relevance_scores_1) if relevance_scores_1 else 0
        relevance_median_2 = np.median(relevance_scores_2) if relevance_scores_2 else 0
        quality_median_1 = np.median(quality_scores_1) if quality_scores_1 else 0
        quality_median_2 = np.median(quality_scores_2) if quality_scores_2 else 0
        
        # Calculate the difference in medians (source1 - source2)
        relevance_median_diff = relevance_median_1 - relevance_median_2
        quality_median_diff = quality_median_1 - quality_median_2

        metrics.append({
            "query": query,
            f"high_relevance_evidence_{source1_name}": relevant_evidence_1,
            f"high_relevance_evidence_{source2_name}": relevant_evidence_2,
            f"quality_evidence_{source1_name}": quality_evidence_1,
            f"quality_evidence_{source2_name}": quality_evidence_2,
            "relevance_median_diff": relevance_median_diff,
            "quality_median_diff": quality_median_diff,
            "better_source_more_relevant_evidence": source1_name if relevant_evidence_1 >= relevant_evidence_2 else source2_name,
            "better_source_higher_quality_evidence": source1_name if quality_evidence_1 >= quality_evidence_2 else source2_name,
            "better_source_relevance_median": source1_name if relevance_median_diff > 0 else source2_name,
            "better_source_quality_median": source1_name if quality_median_diff > 0 else source2_name,
        })

    return pd.DataFrame(metrics)

def evaluate_data_at_compare_evidences(df1, df2, source1_name="lightrag", source2_name="punarayog", output_csv="comparison_results.csv"):
    """Compare evidences between the two sources"""
    df1 = df1.rename(columns={
        "relevance": f"relevance_{source1_name}",
        "quality_assessment": f"quality_assessment_{source1_name}",
        "text": f"evidence_{source1_name}",
        "chunks": f"chunks_{source1_name}"
    })
    df2 = df2.rename(columns={
        "relevance": f"relevance_{source2_name}",
        "quality_assessment": f"quality_assessment_{source2_name}",
        "text": f"evidence_{source2_name}",
        "chunks": f"chunks_{source2_name}"
    })
    
    merged_df = pd.merge(df1, df2, on="query", how="outer", suffixes=("_left", "_right"))
    
    metrics = []
    for query, group in merged_df.groupby("query"):

        lightrag_evidences = group.get(f"evidence_{source1_name}", pd.Series()).dropna().tolist()
        punarayog_evidences = group.get(f"evidence_{source2_name}", pd.Series()).dropna().tolist()
        lightrag_chunks = group.get(f"chunks_{source1_name}", pd.Series()).dropna().values.tolist()
        punarayog_chunks = group.get(f"chunks_{source2_name}", pd.Series()).dropna().values.tolist()

        try:
            api_payload = {
                "query": query,
                "lightrag_evidences": lightrag_evidences,
                "punarayog_evidences": punarayog_evidences
            }
            response = requests.post(
                "http://localhost:8080/compare_evidence", 
                json=api_payload,
                allow_redirects=True,
                timeout=60
            )
            if response.status_code == 307:
                # Follow redirect manually if needed
                redirect_url = response.headers['Location']
                response = requests.post(
                    redirect_url,
                    json=api_payload,
                    timeout=45
                )
            api_result = response.json() if response.status_code == 200 else {}
        except Exception as e:
            print(f"Error processing query: {query}. Error: {str(e)}")
            api_result = {}

        row = {
            "Query": query,
            "Chunks from LightRag": "\n\n".join(lightrag_chunks),
            "Chunks from Punarayog": "\n\n".join(punarayog_chunks),
            "Evidences from Lightrag": "\n\n".join(lightrag_evidences),
            "Evidences from Punarayog": "\n\n".join(punarayog_evidences),
            "Common Evidences": json.dumps(api_result.get("common_evidences", [])),
            "Evidences uniquely available on Lightrag": "\n\n".join([e["text"] for e in api_result.get("unique_lightrag_evidences", [])]),
            "Evidences uniquely available on Punarayog": "\n\n".join([e["text"] for e in api_result.get("unique_punarayog_evidences", [])]),
        }

        metrics.append(row)
        print(f"Common Evidences Found: {len(api_result.get('common_evidences', []))}")
        print(f"Evidences uniquely available on Lightrag: {len(api_result.get('unique_lightrag_evidences', []))}")
        print(f"Evidences uniquely available on Punarayog: {len(api_result.get('unique_punarayog_evidences', []))}")
        print(f"Processed {len(metrics)} queries.")
        # if len(metrics)>50:
        #     break

    final_df = pd.DataFrame(metrics)
    final_df.to_csv(output_csv, index=False)
    return final_df

def main():
    # Load data
    df_punarayog, df_lightrag = load_data()

    df_lightrag.drop(columns=['chunks'], inplace=True)
    df_lightrag_raw_context = pd.read_csv("context_separated.csv")[['id','query','chunks_context','entities_context','relations_context']]
    df_lightrag = pd.merge(
        df_lightrag,
        df_lightrag_raw_context[['query', 'chunks_context']],
        on='query',
        how='left'
    )
    df_lightrag.rename(columns={'chunks_context': 'chunks'}, inplace=True)

    print(f"Light Rag Chunks: {df_lightrag['chunks'].nunique()}")
    print(f"Light Rag Text: {df_lightrag['text'].nunique()}")
    
    # Perform query-level evaluation
    query_metrics = evaluate_data_at_query_level(df_lightrag, df_punarayog)
    query_metrics.to_csv('query_level_metrics_comparison.csv', index=False)
    
    # Print summary statistics
    print("\nSource comparison statistics:")
    print("\nBetter source for relevant evidence:")
    print(query_metrics["better_source_more_relevant_evidence"].value_counts())
    print("\nBetter source for quality evidence:")
    print(query_metrics["better_source_higher_quality_evidence"].value_counts())
    print("\nBetter source by relevance median:")
    print(query_metrics["better_source_relevance_median"].value_counts())
    print("\nBetter source by quality median:")
    print(query_metrics["better_source_quality_median"].value_counts())
    
    # Perform evidence comparison
    evidence_metrics = evaluate_data_at_compare_evidences(df_lightrag, df_punarayog)
    print("\nEvidence comparison completed and saved to CSV")

if __name__ == "__main__":
    main()