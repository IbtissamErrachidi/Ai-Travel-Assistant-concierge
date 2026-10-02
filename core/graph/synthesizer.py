import logging
from langchain_core.messages import HumanMessage

# Importe l'objet llm centralisé
from core.configs import llm
from .prompt import FINAL_ANSWER_PROMPT

logger = logging.getLogger(__name__)

class FinalSynthesizer:
    def __init__(self, model_instance=None):
        self.llm = model_instance if model_instance is not None else llm

    def generate(self, state) -> str:
        combined_context = state.get("synthesis_context") or state.get("final_response", "")
        original_query = state.get("user_query", "")
        chat_history = state.get("chat_history", "") or "Aucun historique disponible."
        conversation_summary = state.get("conversation_summary", "") or "Aucun résumé disponible."
        sources = state.get("sources", [])
        source_names = ", ".join([s.get("title", "Document") for s in sources])

        prompt = FINAL_ANSWER_PROMPT.format(
            conversation_summary=conversation_summary,
            chat_history=chat_history,
            source_names=source_names if source_names else "Aucune source externe",
            combined_context=combined_context,
            original_query=original_query,
        )

        full_response = ""
        try:
            for chunk in self.llm.stream([HumanMessage(content=prompt)]):
                content = chunk.content
                full_response += content
        except Exception as e:
            logger.error(f"Erreur pendant le streaming: {e}")
            try:
                response = self.llm.invoke([HumanMessage(content=prompt)])
                full_response = response.content
            except Exception as e2:
                logger.error(f"Erreur invoke de secours: {e2}")
                full_response = "Je suis désolé, je rencontre une difficulté technique pour formuler ma réponse."

        return full_response.strip()