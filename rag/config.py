from pathlib import Path

# -- Modèles --
DENSE_MODEL = "intfloat/multilingual-e5-base"
SPARSE_MODEL = "Qdrant/bm25"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# -- Qdrant (Port isolé 16333) --
QDRANT_HOST = "localhost"
QDRANT_PORT = 16333
COLLECTION_NAME = "travel_assistant_chunks"

# -- Paramètres Retrieval --
TOP_K_RETRIEVAL = 10
TOP_K_FINAL = 3
DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"