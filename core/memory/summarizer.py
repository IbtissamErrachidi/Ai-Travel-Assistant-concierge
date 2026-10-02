import logging

from langchain_core.messages import HumanMessage

# Importe l'objet llm centralisé
from core.configs import llm
from core.memory.prompt import SUMMARY_UPDATE_PROMPT 

logger = logging.getLogger("ConversationMemorySummarizer")


class ConversationMemorySummarizer:
    def __init__(self, model_instance=None):
        self.llm = model_instance if model_instance is not None else llm

    def update_summary(self, existing_summary: str, recent_turns: str) -> str:
        """
        Met à jour le résumé persistant d'une conversation à partir du résumé actuel
        et des derniers échanges utilisateur/assistant.
        """
        if not recent_turns.strip():
            return existing_summary

        prompt = SUMMARY_UPDATE_PROMPT.format(
            existing_summary=existing_summary if existing_summary else "Aucun résumé pour le moment.",
            recent_turns=recent_turns.strip(),
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            updated_summary = response.content.strip()
            return updated_summary or existing_summary
        except Exception as exc:
            logger.error(f"[SUMMARY UPDATE ERROR]: {exc}")
            return existing_summary