import asyncio
import logging

from core.graph.workflow import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


async def ask_travel_assistant(query):
    """Lance une requête dans le graphe Travel Assistant."""

    print("\n" + "=" * 60)
    print(f"QUESTION : {query}")
    print("=" * 60)

    inputs = {
        "user_query": query,
        "chat_history": "",
        "conversation_summary": "",
        "plan": [],
        "needs_clarification": False,
        "clarification_question": None,
        "retrieved_chunks": [],
        "tool_results": [],
        "synthesis_context": "",
        "final_answer": "",
        "final_response": "",
        "sources": []
    }

    try:
        result = await app.ainvoke(inputs)

        print(f"\nPLAN : {result.get('plan')}")
        print(f"NEEDS CLARIFICATION : {result.get('needs_clarification')}")

        print(
            f"\nREPONSE DE L'ASSISTANT :\n"
            f"{result.get('final_response')}"
        )

        if result.get("sources"):
            sources_titles = [
                s["title"]
                for s in result.get("sources", [])
            ]
            print("Sources : " + ", ".join(sources_titles))

    except Exception as e:
        print(f"ERREUR LORS DE L'EXECUTION : {e}")


if __name__ == "__main__":

    query = "Quel est le statut du vol AH1235 aujourd'hui ?"
    # query = "Quels sont les objets interdits en cabine ?"
    # query = "Trouve-moi un vol Paris-Alger vendredi."
    # query = "Trouve-moi un vol Paris-Alger le 2026-10-02."
    # query = "Mon vol AH1235 est annulé. Est-ce que je peux demander un remboursement ?"
    # query = "Quel est le statut du vol AH1235 aujourd'hui et si il est annulé, quelles sont les conditions de remboursement ?"


    asyncio.run(ask_travel_assistant(query))