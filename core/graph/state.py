from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict

class AgentState(TypedDict):
    """
    État partagé à travers les nœuds du graphe de l'assistant de voyage.
    """
    # Identifiant de session (pour la mémoire persistante)
    session_id: str

    # Requête utilisateur
    user_query: str
    chat_history: str
    conversation_summary: str

    # Compteur de messages (pour déclencher le summarizer tous les 20 messages)
    message_count: int

    # Champs du Planner
    plan: List[Any]
    needs_clarification: bool
    clarification_question: Optional[str]

    # Données RAG et Outils
    retrieved_chunks: List[str]
    tool_results: List[Any]
    synthesis_context: str

    # Sortie finale
    final_answer: str
    final_response: str
    sources: List[dict]