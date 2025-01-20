config_file="s3://docketai-config/credentials/rds_foundry_proxy_{}.json"
chunks_table="foundry.chunk_embeddings_view"
subgraph_sources={
    "googledrive": ["PK"],
    "manual.seismic": ["PK"],
}
    