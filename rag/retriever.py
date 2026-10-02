import logging
import numpy as np
from typing import List, Dict, Optional

from qdrant_client.models import SparseVector, FusionQuery, Prefetch, Fusion
from fastembed import SparseTextEmbedding
from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient


from .config import *
from .schemas import RetrievedChunk

logger = logging.getLogger("retriever")

class HybridRetriever:
    def __init__(self):
        logger.info("Initialisation du moteur de recherche hybride (Travel Assistant)...")

        # Modèles d'embedding
        self.dense_model = SentenceTransformer(DENSE_MODEL)
        self.sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL)

        # Modèle de Reranking (Cross-Encoder)
        self.reranker = CrossEncoder(RERANKER_MODEL, max_length=512)

        # Client Qdrant (port 16333)
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    def _encode_dense(self, query: str) -> List[float]:
        """Encode la requête pour le modèle Dense (E5) avec le préfixe obligatoire."""
        return self.dense_model.encode(
            f"query: {query}", 
            normalize_embeddings=True
        ).tolist()

    def _encode_sparse(self, query: str) -> SparseVector:
        """Encode la requête pour le modèle Sparse (BM25) et retourne un SparseVector Qdrant."""
        result = list(self.sparse_model.embed(query))[0]
        return SparseVector(
            indices=result.indices.tolist(),
            values=result.values.tolist(),
        )

    def retrieve(self, query: str, top_k: int = TOP_K_RETRIEVAL) -> List[Dict]:
        """Étape 1 : Récupération hybride (Dense + Sparse + RRF) depuis Qdrant."""
        dense_v = self._encode_dense(query)
        sparse_v = self._encode_sparse(query)

        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=[
                Prefetch(query=dense_v, using=DENSE_VECTOR_NAME, limit=top_k),
                Prefetch(query=sparse_v, using=SPARSE_VECTOR_NAME, limit=top_k),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )

        return [
            {
                "id": p.id,
                "score_rrf": p.score,
                "text": p.payload.get("text", ""),
                "source": p.payload.get("source", ""),
                "metadata": p.payload.get("metadata", {}),
            }
            for p in results.points
        ]

    def rerank(self, query: str, chunks: List[Dict], top_k: int = TOP_K_FINAL) -> List[RetrievedChunk]:
        """Étape 2 : Ré-ordonnancement des chunks récupérés via le Cross-Encoder."""
        if not chunks:
            return []

        # Préparation des paires (requête, texte du chunk)
        pairs = [(f"query: {query.strip()}", f"passage: {c['text'].strip()}") for c in chunks]

        # Calcul des scores par le Cross-Encoder
        scores = self.reranker.predict(pairs)

        for chunk, score in zip(chunks, scores):
            chunk["score_reranker"] = float(score)

        # Tri par ordre décroissant du score de reranking
        reranked = sorted(chunks, key=lambda x: x["score_reranker"], reverse=True)

        # Conversion en objets Pydantic (RetrievedChunk)
        return [RetrievedChunk(**c) for c in reranked[:top_k]]

    def search(self, query: str) -> List[RetrievedChunk]:
        """Pipeline principal de recherche."""
        logger.info(f"Recherche pour la requête : '{query}'")

        # 1. Récupération des candidats (ex: top 10)
        candidates = self.retrieve(query, top_k=TOP_K_RETRIEVAL)
        logger.info(f"{len(candidates)} candidats récupérés depuis Qdrant.")

        # 2. Reranking pour garder les meilleurs (ex: top 3)
        final_chunks = self.rerank(query, candidates, top_k=TOP_K_FINAL)
        logger.info(f"{len(final_chunks)} chunks retenus après reranking.")

        return final_chunks