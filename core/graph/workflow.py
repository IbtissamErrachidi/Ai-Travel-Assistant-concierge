import logging
import asyncio
from langgraph.graph import StateGraph, END, START
from .state import AgentState
from rag.retriever import HybridRetriever

from core.planner.planner import AgentPlanner
from core.fallback_agent.fallback_agent import FallbackAgent
from .synthesizer import FinalSynthesizer

# Import du module de mémoire
from core.memory.summarizer import ConversationMemorySummarizer

# Import de tes outils de vol (SQLite)
from tools.flight_tools import search_flights, get_flight_status, get_airport_info, get_booking

logger = logging.getLogger("TravelAssistant_Graph")

# =========================
# INIT COMPONENTS
# =========================

planner = AgentPlanner()
fallback = FallbackAgent()
final_synthesizer = FinalSynthesizer()
retriever = HybridRetriever()
memory_summarizer = ConversationMemorySummarizer()  # <--- Initialisation du summarizer

# =========================
# PLANNER NODE
# =========================

def planner_node(state: AgentState):
    logger.info("--- NODE: PLANNER ---")
    result = planner.plan(
        query=state["user_query"],
        chat_history=state.get("chat_history", ""),
        conversation_summary=state.get("conversation_summary", "")
    )
    return {
        "plan": result.steps,
        "needs_clarification": result.needs_clarification,
        "clarification_question": result.clarification_question
    }

# =========================
# PLANNER LOGIC
# =========================

def planner_logic(state: AgentState):
    print(f"\n--- DEBUG LOGIC ---")
    print(f"Plan present in state? : {'Yes' if state.get('plan') else 'No'}")
    print(f"Plan content: {state.get('plan')}")
    print(f"Needs Clarification? : {state.get('needs_clarification')}")

    if state.get("needs_clarification") is True:
        print("-> Direction: FALLBACK (clarification requested)")
        return "fallback"

    plan = state.get("plan")
    if plan is None or len(plan) == 0:
        # Si un historique de conversation ou un résumé existe, l'utilisateur pose une question de suivi
        # On passe directement au synthétiseur pour qu'il réponde grâce à la mémoire et au contexte
        history = (state.get("chat_history") or "").strip()
        summary = (state.get("conversation_summary") or "").strip()
        if history or summary:
            print("-> Direction: SYNTHESIZER (contextual follow-up without extra tools)")
            return "synthesizer"
        print("-> Direction: FALLBACK (initial greeting or empty plan)")
        return "fallback"

    print(f"-> Direction: EXECUTE_PLAN (steps: {len(plan)})")
    return "execute_plan"

# =========================
# EXECUTE PLAN NODE (ASYNC & PARALLEL)
# =========================

async def execute_plan_node(state: AgentState):
    logger.info("--- NODE: EXECUTE PLAN (PARALLEL) ---")
    plan = state.get("plan")
    
    if not plan:
        return {"current_route": "FALLBACK"}

    async def run_step(step):
        tool_type = step.tool       # "RAG" ou "TOOL"
        tool_name = step.tool_name
        args = step.arguments or {}  # Dictionnaire d'arguments

        try:
            if tool_type == "RAG":
                query = args.get("query", "")
                logger.info(f"Exécution du vrai RAG (Hybrid Search) pour : {query}")
                
                try:
                    retrieved_chunks = await asyncio.to_thread(retriever.search, query)
                    
                    formatted_texts = []
                    sources_list = []
                    
                    for chunk in retrieved_chunks:
                        formatted_texts.append(f"--- Extrait Documentaire ---\n{chunk.text}")
                        source_title = chunk.metadata.get("source", "Guide Réglementaire Voyage")
                        sources_list.append({"title": source_title, "type": "rag"})
                    
                    rag_result_text = "\n\n".join(formatted_texts) if formatted_texts else "Aucun document pertinent trouvé."
                    
                    return {
                        "type": "RAG",
                        "context": f"[RAG Chunks Réels]:\n{rag_result_text}",
                        "source": sources_list[0] if sources_list else {"title": "Guide Réglementaire Voyage", "type": "rag"}
                    }
                except Exception as e:
                    logger.error(f"Erreur lors de l'exécution du RAG: {e}")
                    return {
                        "type": "RAG",
                        "context": "[RAG Erreur]: Impossible d'interroger la base documentaire.",
                        "source": {"title": "Erreur RAG", "type": "rag"}
                    }

            elif tool_type == "TOOL":
                logger.info(f"Exécution TOOL '{tool_name}' avec arguments : {args}")
                tool_result = None

                if tool_name == "get_flight_status":
                    flight_num = args.get("flight_number") or args.get("query", "")
                    tool_result = await asyncio.to_thread(get_flight_status, flight_number=flight_num)
                    
                elif tool_name == "get_airport_info":
                    airport_code = args.get("airport_code") or args.get("query", "")
                    tool_result = await asyncio.to_thread(get_airport_info, airport_code=airport_code)
                    
                elif tool_name == "get_booking":
                    booking_ref = args.get("booking_reference") or args.get("query", "")
                    tool_result = await asyncio.to_thread(get_booking, booking_reference=booking_ref)
                    
                elif tool_name == "search_flights":
                    orig = args.get("origin", "Paris")
                    dest = args.get("destination", "Alger")
                    tool_result = await asyncio.to_thread(search_flights, origin=orig, destination=dest)
                    print("RÉSULTAT BRUT DE L'OUTIL :")
                    print(tool_result)
                else:
                    tool_result = {"status": "error", "message": f"Outil {tool_name} inconnu."}

                tool_labels = {
                    "search_flights": "Horaires et disponibilités des vols",
                    "get_flight_status": "Statut et suivi des vols",
                    "get_airport_info": "Informations aéroportuaires",
                    "get_booking": "Dossier de réservation",
                }
                display_title = tool_labels.get(tool_name, "Service de conciergerie voyage")

                return {
                    "type": "TOOL",
                    "context": f"[Données de vol {tool_name}]: {tool_result}",
                    "source": {"title": display_title, "type": "tool"}
                }
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'étape {tool_name}: {e}")
            return None

    tasks = [run_step(step) for step in plan]
    results = await asyncio.gather(*tasks)

    retrieved_contexts = []
    sources = []

    for res in results:
        if res:
            retrieved_contexts.append(res["context"])
            sources.append(res["source"])

    if not retrieved_contexts:
        return {"current_route": "FALLBACK"}

    final_text_context = "\n\n".join(retrieved_contexts)

    return {
        "synthesis_context": final_text_context,
        "sources": sources,
        "current_route": "DONE"
    }

# =========================
# SYNTHESIZER NODE
# =========================

def call_final_llm(state: AgentState):
    logger.info("--- NODE: FINAL SYNTHESIZER ---")
    answer = final_synthesizer.generate(state)
    return {
        "final_answer": answer,
        "final_response": answer,
        "sources": state.get("sources", []),
    }

# =========================
# FALLBACK NODE
# =========================

def fallback_node(state: AgentState):
    logger.info("--- NODE: FALLBACK ---")
    
    query = (state.get("user_query") or "").strip().lower()
    
    # Réponses instantanées pour les salutations courantes (zéro latence)
    quick_greetings = {
        "hello": "Hello! I'm your travel assistant. How can I help you today?",
        "hi": "Hi there! I'm your travel assistant. How can I help you today?",
        "hey": "Hey! How can I assist you with your travel plans today?",
        "bonjour": "Bonjour ! Je suis votre assistant de voyage intelligent. Comment puis-je vous aider aujourd'hui ?",
        "salut": "Salut ! Comment puis-je vous aider pour vos voyages aujourd'hui ?",
        "مرحباً": "مرحباً! أنا مساعد السفر الذكي الخاص بك. كيف يمكنني مساعدتك اليوم؟",
        "سلام": "وعليكم السلام! كيف يمكنني مساعدتك في سفرك اليوم؟"
    }
    
    # Si l'utilisateur tape une salutation simple, on répond instantanément dans sa langue
    if query in quick_greetings and not state.get("needs_clarification"):
        res_message = quick_greetings[query]
    else:
        class SimpleRoute:
            query = state.get("user_query", "")

        class SimpleRoutingResult:
            needs_clarification = state.get("needs_clarification", False)
            clarification_question = state.get("clarification_question")

        if not state.get("needs_clarification") and not state.get("plan"):
            res_message = "Bonjour ! Je suis votre assistant de voyage intelligent. Comment puis-je vous aider aujourd'hui ?"
        else:
            res = fallback.generate_response(SimpleRoute(), SimpleRoutingResult())
            res_message = res.message

    return {
        "final_answer": res_message,
        "final_response": res_message,
        "retrieved_chunks": [],
        "sources": []
    }

# =========================
# MEMORY SUMMARIZER NODE (NOUVEAU)
# =========================

def summarizer_node(state: AgentState):
    logger.info("--- NODE: MEMORY SUMMARIZER ---")

    message_count = state.get("message_count", 0) + 1

    existing_summary = state.get("conversation_summary", "")
    user_query = state.get("user_query", "")
    assistant_response = state.get("final_response", "")

    # Déclenche la mise à jour du résumé uniquement tous les 20 messages
    if message_count % 20 == 0:
        logger.info(f"[SUMMARIZER] Déclenchement à message #{message_count}")
        recent_turns = f"Utilisateur: {user_query}\nAssistant: {assistant_response}"
        updated_summary = memory_summarizer.update_summary(
            existing_summary=existing_summary,
            recent_turns=recent_turns
        )
    else:
        logger.info(f"[SUMMARIZER] Passage ({message_count}/20) — pas de mise à jour du résumé")
        updated_summary = existing_summary

    return {
        "conversation_summary": updated_summary,
        "message_count": message_count,
    }

# =========================
# EXECUTE LOGIC
# =========================

def execute_logic(state: AgentState):
    if state.get("current_route") == "FALLBACK":
        return "fallback"
    return "end"

# =========================
# BUILD WORKFLOW
# =========================

def build_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)

    # Ajout des nœuds
    workflow.add_node("planner", planner_node)
    workflow.add_node("execute_plan", execute_plan_node)
    workflow.add_node("final_synthesizer", call_final_llm)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("summarizer", summarizer_node)  # <--- Ajout du nœud mémoire

    # Point de départ
    workflow.add_edge(START, "planner")

    # Transitions du planner
    workflow.add_conditional_edges(
        "planner",
        planner_logic,
        {
            "execute_plan": "execute_plan",
            "fallback": "fallback",
            "synthesizer": "final_synthesizer",
        }
    )

    # Transitions après l'exécution du plan
    workflow.add_conditional_edges(
        "execute_plan",
        execute_logic,
        {
            "end": "final_synthesizer",
            "fallback": "fallback"
        }
    )

    # Connexion de la fin des flux de réponse vers le summarizer
    workflow.add_edge("final_synthesizer", "summarizer")
    workflow.add_edge("fallback", "summarizer")

    # Le summarizer clôture le graphe pour ce tour
    workflow.add_edge("summarizer", END)

    return workflow

app = build_workflow().compile()