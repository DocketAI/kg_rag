import json
import boto3
import psycopg2
from random import randint
from .base import TextChunkSchema
from .utils import encode_string_by_tiktoken, merge_content
from .prompt import AGG_CHUNK_SEP
from .config import (
    config_file,
    chunks_table,
    subgraph_sources,
)


def get_file(file, env):
    file = file.format(env)
    s3_bucket = file.split("/")[2]
    prefix = "/".join(file.split("/")[3:])
    return s3_bucket, prefix


def read_config(file, env):
    s3_bucket, prefix = get_file(file, env)
    s3 = boto3.resource("s3")
    content_object = s3.Object(s3_bucket, prefix)
    file_content = content_object.get()["Body"].read().decode("utf-8")
    return file_content

def db_connection(env):
    creds = read_config(config_file, env)
    creds = json.loads(creds)
    rds_client = boto3.client("rds")
    auth_token = rds_client.generate_db_auth_token(
        DBHostname=creds["host"],
        Port=creds["port"],
        DBUsername=creds["user"],
        Region=creds["region"],
    )
    return psycopg2.connect(
        user=creds["user"],
        password=auth_token,
        host=creds["host"],
        port=creds["port"],
        database=creds["db"],
        sslmode="require",
    )


def get_chunks(
    min_tokens: int,
    company_id: int,
    batch_size: int = 100,
):
    connection = None
    try:
        connection = db_connection("dev")
        cursor = connection.cursor()

        count_query = f"SELECT COUNT(*) FROM {chunks_table} where company_id = {company_id}"
        cursor.execute(count_query)
        total_rows = cursor.fetchone()[0]

        combined_chunks = []

        current_source_id = None
        current_chunk_ids = []
        current_contents = []
        current_tokens = 0
        combined_sequence = 0

        offset = 0
        while offset < total_rows:
            query = f"""
                SELECT chunk_id, content, sequence, source_id, source
                FROM {chunks_table} WHERE company_id = {company_id}
                ORDER BY source_id, sequence
                LIMIT {batch_size} OFFSET {offset}
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            if not rows:
                break

            for (chunk_id, content, sequence, source_id, source) in rows:

                if current_source_id is not None and source_id != current_source_id:
                    if current_chunk_ids:
                        combined_chunk_id = AGG_CHUNK_SEP.join(current_chunk_ids)
                        merged_content = merge_content(current_contents)
                        combined_chunks.append({
                            "tokens": current_tokens,
                            "chunk_id": combined_chunk_id,
                            "content": merged_content,
                            "sequence": combined_sequence,
                            "source_id": current_source_id,
                            "subgraphs": subgraph_sources.get(source, []) + ['ALL'],
                        })
                        current_chunk_ids = []
                        current_contents = []
                        current_tokens = 0
                        combined_sequence = 0

                if current_source_id != source_id:
                    current_source_id = source_id

                tokens = len(encode_string_by_tiktoken(content))
                current_chunk_ids.append(chunk_id)
                current_contents.append(content)
                current_tokens += tokens

                if current_tokens >= min_tokens:
                    combined_chunk_id = AGG_CHUNK_SEP.join(current_chunk_ids)
                    merged_content = merge_content(current_contents)
                    combined_chunks.append({
                        "tokens": current_tokens,
                        "chunk_id": combined_chunk_id,
                        "content": merged_content,
                        "sequence": combined_sequence,
                        "source_id": current_source_id,
                        "subgraphs": subgraph_sources.get(source, []) + ['ALL'],
                    })
                    
                    combined_sequence += 1

                    current_chunk_ids = []
                    current_contents = []
                    current_tokens = 0

            print(f"read {offset} rows of total {total_rows}")
            offset += batch_size 

        if current_tokens > 0:
            combined_chunk_id = AGG_CHUNK_SEP.join(current_chunk_ids)
            merged_content = merge_content(current_contents)
            combined_chunks.append({
                "tokens": current_tokens,
                "chunk_id": combined_chunk_id,
                "content": merged_content,
                "sequence": combined_sequence,
                "source_id": current_source_id,
                "subgraphs": subgraph_sources.get(source, []) + ['ALL'],
            })
            
        return {
            ch["chunk_id"]: TextChunkSchema(
                            tokens=ch["tokens"],
                            content=ch["content"],
                            full_doc_id=str(ch["source_id"]),
                            chunk_order_index=ch["sequence"],
                            subgraphs=ch["subgraphs"]
                        )
            for ch in combined_chunks
        }

    except Exception as e:
        print("Error occurred:", e)
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    get_chunks(
        min_tokens=1200,
        batch_size=100,
        company_id=18,
    )
