import logging
import json
import re

from langchain_core.messages import HumanMessage


from core.configs import llm
from .prompt import PLANNER_PROMPT
from .schemas import PlanResult, PlanStep

logger = logging.getLogger(__name__)

class AgentPlanner:
    def __init__(self, model_instance=None):
        # Utilise l'instance centralisée par défaut, ou une instance personnalisée si fournie
        self.llm = model_instance if model_instance is not None else llm

    def plan(
        self,
        query: str,
        chat_history: str = "",
        conversation_summary: str = "",
    ) -> PlanResult:
        try:
            query = query.strip()
            prompt = PLANNER_PROMPT.format(
                query=query,
                chat_history=chat_history if chat_history else "Aucun historique utile.",
                conversation_summary=conversation_summary if conversation_summary else "Aucun résumé utile.",
            )

            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            logger.info(f"[PLANNER RAW]: {content}")

            parsed = self._safe_parse(content)
            
            # Construction sécurisée des PlanStep avec gestion propre des arguments
            steps = []
            for s in parsed.get("steps", []):
                tool = s.get("tool")
                tool_name = s.get("tool_name")
                arguments = s.get("arguments", {})
                
                if not arguments and "query" in s:
                    arguments = {"query": s.get("query")}

                steps.append(PlanStep(tool=tool, tool_name=tool_name, arguments=arguments))

            return PlanResult(
                steps=steps,
                needs_clarification=parsed.get("needs_clarification", False),
                clarification_question=parsed.get("clarification_question")
            )

        except Exception as e:
            logger.error(f"[PLANNER ERROR]: {e}")
            return PlanResult(
                steps=[],
                needs_clarification=True,
                clarification_question="Pouvez-vous reformuler votre question concernant votre voyage ?"
            )

    def _safe_parse(self, text: str):
        try:
            text = re.sub(r'//.*', '', text)
            text = text.replace("```json", "").replace("```", "")
            text = re.sub(r'\s+', ' ', text).strip()

            start = text.find("{")
            end = text.rfind("}")

            if start == -1 or end == -1:
                return {"steps": [], "needs_clarification": True, "clarification_question": "Format JSON introuvable"}

            text = text[start:end+1]

            try:
                return json.loads(text)
            except json.JSONDecodeError:
                text_cleaned = re.sub(r',\s*([\]}])', r'\1', text)
                return json.loads(text_cleaned)

        except Exception as e:
            logger.error(f"[PLANNER JSON LOAD FAIL]: {text} | error={e}")
            return {
                "steps": [],
                "needs_clarification": True,
                "clarification_question": "Désolé, je rencontre une difficulté technique pour organiser votre demande. Pouvez-vous reformuler ?"
            }