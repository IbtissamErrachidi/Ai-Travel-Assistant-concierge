from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PlanStep(BaseModel):
    tool: str  # RAG | TOOL
    tool_name: Optional[str] = None  # Ex: hybrid_search, search_flights, get_flight_status, etc.
    arguments: Dict[str, Any] = Field(default_factory=dict)  # Paramètres extraits pour la fonction

class PlanResult(BaseModel):
    steps: List[PlanStep]
    needs_clarification: bool = False
    clarification_question: Optional[str] = None