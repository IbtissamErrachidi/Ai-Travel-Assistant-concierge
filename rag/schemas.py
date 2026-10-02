from typing import List, Dict, Optional, Any
from pydantic import BaseModel

class RetrievedChunk(BaseModel):
    id: str
    text: str
    source: str = "Unknown"
    score_rrf: Optional[float] = 0.0
    score_reranker: Optional[float] = None
    metadata: Dict[str, Any] = {}
    chunk_type: Optional[str] = "text"

class SearchResult(BaseModel):
    query: str
    chunks: List[RetrievedChunk]