SUMMARY_UPDATE_PROMPT = """
Tu maintiens un résumé durable d'une conversation pour un assistant RAG d'entreprise.

[RÈGLES]
1. Garde uniquement les informations utiles pour les prochains tours.
2. Préserve les faits durables : sujet, objectif utilisateur, étapes déjà tentées, décisions prises, blocages restants.
3. Ignore les salutations, remerciements et répétitions sans valeur.
4. N'invente rien. Si une information n'est pas présente, ne l'ajoute pas.
5. Réponds avec un résumé court en texte brut, maximum 6 lignes.

[RÉSUMÉ ACTUEL]
{existing_summary}

[NOUVEAUX ÉCHANGES]
{recent_turns}

[RÉSUMÉ MIS À JOUR]
"""
