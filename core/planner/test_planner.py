import logging
from core.planner.planner import AgentPlanner

# Configuration des logs pour afficher les détails dans la console
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_agent_planner():
    print("=== DÉBUT DU TEST DU PLANNER ===")
    
    # Initialisation du planner (utilise le modèle configuré dans core/configs.py)
    planner = AgentPlanner()

    # Liste de requêtes diversifiées pour valider le routage (RAG, TOOL, Mixte, Salutation, Hors-sujet)
    queries = [
        "Bonjour, j'ai besoin d'aide pour mon voyage.",
        "Comment puis-je me faire rembourser mon billet d'avion annulé ?",
        "Est-ce que le vol AF789 de demain est à l'heure ?",
        "Quelles sont les dimensions maximales pour un bagage à main et est-ce que le vol AT202 est programmé ?",
        "Où est-ce que je peux trouver le meilleur couscous à Casablanca ?",
        "Quels documents d'identité sont obligatoires pour un vol international ?",
        "Salut !",
        "Mon vol a été retardé de 3 heures, quelles sont mes indemnités et quel est le statut du vol AH1020 ?"
    ]

    for i, q in enumerate(queries, 1):
        print(f"\n--------------------------------------------------")
        print(f"Test {i} - Requête utilisateur : '{q}'")
        print(f"--------------------------------------------------")
        
        # Appel de la méthode plan (sans historique ni mémoire)
        result = planner.plan(query=q)

        # Affichage du résultat structuré
        print(f"Besoin de clarification ? : {result.needs_clarification}")
        if result.needs_clarification:
            print(f"Question de clarification : {result.clarification_question}")
        else:
            print("Étapes générées (Plan) :")
            if not result.steps:
                print("    (Aucune étape - Liste vide, ex: salutation)")
            for step_idx, step in enumerate(result.steps, 1):
                print(f"    Étape {step_idx}:")
                print(f"      - Outil (Tool/RAG) : {step.tool}")
                print(f"      - Nom de l'outil     : {step.tool_name}")
                print(f"      - Arguments          : {step.arguments}")

    print("\n=== FIN DU TEST DU PLANNER ===")

if __name__ == "__main__":
    test_agent_planner()