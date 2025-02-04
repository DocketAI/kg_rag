env="app"
config_file="s3://docketai-config/credentials/rds_foundry_proxy_{}.json"
chunks_table="foundry.chunk_embeddings_view"
subgraph_sources={
    "googledrive": ["PK"],
    "manual.seismic": ["PK"],
}
insert_batch_size=10
min_chunk_tokens=1200
    