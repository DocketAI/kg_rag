env="dev"
config_file="s3://docketai-config/credentials/rds_foundry_proxy_{}.json"
chunks_table="foundry.chunk_embeddings_view"
subgraph_sources={
    "googledrive": ["PK"],
    "manual.seismic": ["PK"],
}
insert_batch_size=5
min_chunk_tokens=1200
include_known_entities=False
    