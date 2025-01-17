config_file="s3://docketai-config/credentials/rds_foundry_proxy_{}.json"
chunks_table="foundry.chunk_embeddings_view"
subgraph_sources={
    "googledrive": ["PK"],
    "manual.seismic": ["PK"],
    "web": ["WEB"],
    "slack": ["SLACK"],
    "confluence": ["OT"],
    "custom.chorus": ["OT"],
    "custom.crayon": ["OT"],
    "manual.crayon": ["OT"],
}
    