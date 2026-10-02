import logging
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from .prompt import FALLBACK_PROMPT
from .schemas import FallbackResponse
from core.configs import LLM_MODEL

logger = logging.getLogger(__name__)

class FallbackAgent:
    def __init__(self, model_name: str = LLM_MODEL):
        self.llm = ChatOllama(
            model=model_name,
            temperature=0.1,
        )

    def generate_response(
        self,
        route_data,
        routing_result,
    ) -> FallbackResponse:
        """
        Génère une réponse textuelle de repli (salutation ou clarification).
        """
        query = route_data.query
        
        if getattr(routing_result, "needs_clarification", False):
            fallback_type = "CLARIFICATION"
            clarification = getattr(routing_result, "clarification_question", None) or "Pouvez-vous reformuler ?"
        else:
            fallback_type = "GREETING"
            clarification = ""

        try:
            formatted_prompt = FALLBACK_PROMPT.format(
                fallback_type=fallback_type,
                query=query,
                clarification_question=clarification
            )

            response = self.llm.invoke([HumanMessage(content=formatted_prompt)])
            return FallbackResponse(message=response.content.strip())

        except Exception as e:
            logger.error(f"[FALLBACK AGENT ERROR]: {str(e)}")
            return FallbackResponse(message="Désolé, je n'ai pas bien compris. Pourriez-vous reformuler votre demande concernant votre voyage ?")