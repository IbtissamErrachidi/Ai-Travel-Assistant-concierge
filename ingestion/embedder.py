"""Embedder module for Travel Assistant RAG.
Reads local JSON chunks, generates Hybrid Embeddings (Dense via E5 + Sparse via FastEmbed),
and indexes them into Qdrant.
"""

import os
import json
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any

from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    VectorParams,
    SparseVectorParams,
    SparseVector,
    Distance,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("embedder")

# Configs Qdrant & Modèles
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 16333))
COLLECTION_NAME = "travel_assistant_chunks"

DENSE_MODEL_NAME = "intfloat/multilingual-e5-base"
SPARSE_MODEL_NAME = "Qdrant/bm25"  

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"
VECTOR_SIZE = 768  # Taille des vecteurs pour multilingual-e5-base

BASE_DIR = Path(__file__).resolve().parents[1]
CHUNKS_DIR = BASE_DIR / "chunks"


def get_embedding_text(content: str) -> str:
    """Ajoute le préfixe obligatoire pour les modèles de la famille E5."""
    return f"passage: {content}"


def create_collection_if_not_exists(client: QdrantClient) -> None:
    """Crée la collection hybride dans Qdrant si elle n'existe pas."""
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in collections:
        logger.info(f"Collection existante : {COLLECTION_NAME}")
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            DENSE_VECTOR_NAME: VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        },
        sparse_vectors_config={
            SPARSE_VECTOR_NAME: SparseVectorParams(),
        },
    )
    logger.info(f"Collection hybride créée avec succès : {COLLECTION_NAME}")


def load_all_chunks() -> List[Dict[str, Any]]:
    """Charge tous les chunks depuis les fichiers JSON individuels dans CHUNKS_DIR."""
    all_chunks = []
    json_files = [f for f in CHUNKS_DIR.glob("*_chunks.json") if f.name != "all_chunks.json"]

    if not json_files:
        logger.warning(f"Aucun fichier JSON de chunks trouvé dans {CHUNKS_DIR}")
        return []

    for file_path in json_files:
        try:
            chunks = json.loads(file_path.read_text(encoding="utf-8"))
            all_chunks.extend(chunks)
        except Exception as e:
            logger.error(f"Erreur lors de la lecture de {file_path.name} : {e}")

    logger.info(f"Total de {len(all_chunks)} chunks chargés à partir de {len(json_files)} fichiers JSON.")
    return all_chunks


def run_embedding_pipeline():
    # 1. Chargement des chunks locaux
    chunks = load_all_chunks()
    if not chunks:
        return

    # 2. Initialisation des modèles et client Qdrant
    logger.info(f"Chargement du modèle Dense ({DENSE_MODEL_NAME})...")
    dense_model = SentenceTransformer(DENSE_MODEL_NAME)

    logger.info(f"Chargement du modèle Sparse ({SPARSE_MODEL_NAME})...")
    sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    create_collection_if_not_exists(client)

    # 3. Génération des Embeddings Denses
    logger.info("Génération des embeddings denses...")
    texts_dense = [get_embedding_text(c["text"]) for c in chunks]
    dense_embs = dense_model.encode(
        texts_dense, batch_size=32, show_progress_bar=True, normalize_embeddings=True
    )

    # 4. Génération des Embeddings Sparse
    logger.info("Génération des embeddings sparse...")
    texts_sparse = [c["text"] for c in chunks]
    sparse_embs = list(sparse_model.embed(texts_sparse))

    # 5. Préparation des Points Qdrant
    points = []
    for i, c in enumerate(chunks):
        payload = {
            "chunk_id": c["chunk_id"],
            "text": c["text"],
            "source": c["source"],
            "type": c.get("type", "text"),
            "metadata": c.get("metadata", {}),
        }

        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    DENSE_VECTOR_NAME: dense_embs[i].tolist(),
                    SPARSE_VECTOR_NAME: SparseVector(
                        indices=sparse_embs[i].indices.tolist(),
                        values=sparse_embs[i].values.tolist(),
                    ),
                },
                payload=payload,
            )
        )

    # 6. Insertion par Batch dans Qdrant
    batch_size = 50
    logger.info(f"Début de l'insertion de {len(points)} points dans Qdrant...")
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        logger.info(f"Batch {i // batch_size + 1} / {(len(points) - 1) // batch_size + 1} inséré.")

    logger.info(" Indexation Hybride terminée avec succès !")


if __name__ == "__main__":
    run_embedding_pipeline()