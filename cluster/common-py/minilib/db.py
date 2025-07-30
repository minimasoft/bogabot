# Copyright (c) 2025 Minimasoft
import base58
import os
from opensearchpy import OpenSearch
from typing import Dict, Any, Optional

# config
DEFAULT_SHARDS=1
DEFAULT_REPLICAS=1
DOCUMENT_ID_SIZE=13


def gen_document_id(data=None) ->  str:
    """
    Document id is a base58 encoded random byte seqence.
    Default size is 13 bytes.
    """
    data = data or os.urandom(DOCUMENT_ID_SIZE) 
    return base58.b58encode(data).decode('utf-8')

def test_gen_document_id():
    assert len(gen_document_id()) > DOCUMENT_ID_SIZE
    assert "TGT5MVaw5aVVuC7tRwX4MX3" == gen_document_id("01234567890123456".encode('utf-8'))
    assert "o1JLFKyouxmG3H1C8mg2inf" == gen_document_id("ThisIsABase58Test".encode('utf-8'))
    print(f"A random id: {gen_document_id()}")


def client_from_env() -> OpenSearch:
    return OpenSearch(
        hosts=[os.getenv("OPENSEARCH_URL", "localhost:9200")],
        http_auth=(os.getenv("OPENSEARCH_USER", "admin"), os.getenv("OPENSEARCH_PASSWORD", "admin")),
        use_ssl=int(os.getenv("OPENSEARCH_USESSL", "1")),
        verify_certs=int(os.getenv("OPENSEARCH_VERIFYSSL", "0"))
    )


class IndexExists(Exception):
    def __init__(self, index_name: str):
        self.index_name = index_name
        super().__init__(f"DB Index '{index_name}' already exists")


def check_index(
    index_name: str,
    client: OpenSearch = None,
    raise_: bool=True,
) -> bool:
    client = client or client_from_env()
    if client.indices.exists(index=index_name) == True:
        if raise_ == True:
            raise IndexExists(index_name)
        else:
            return True
    return False


def create_index(
    index_name: str,
    client: OpenSearch = None,
    settings: Optional[Dict[str, Any]] = None,
    mappings: Optional[Dict[str, Any]] = None,
):
    client = client or client_from_env()

    check_index(index_name, client)

    default_settings = {
        "number_of_shards": DEFAULT_SHARDS,
        "number_of_replicas": DEFAULT_REPLICAS,
    }

    index_body = {
        "settings": settings or default_settings,
    }

    if mappings is not None:
        index_body["mappings"] = mappings

    return client.indices.create(
        index=index_name,
        body=index_body,
    )


def delete_index(
    index_name: str,
    client: OpenSearch = None,
):
    client = client or client_from_env()

    if check_index(index_name, client, False):
        return client.indices.delete(index=index_name)
