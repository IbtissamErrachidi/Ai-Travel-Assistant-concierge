import sys
print("=== DEBUT DU SCRIPT DE TEST ===", flush=True)

from rag.retriever import HybridRetriever
print("HybridRetriever importé avec succès.", flush=True)

if __name__ == "__main__":
    print("Initialisation du retriever...", flush=True)
    retriever = HybridRetriever()
    
    # query = "Quels sont les objets interdits en cabine ?"
    # query = "Quelles sont les conditions tarifaires pour l'Eco Essential et la Family Classic ?"
    # query = "Combien de temps avant le départ dois-je arriver à l'aéroport ?"
    query = "Quels documents sont nécessaires pour voyager ?"
    print(f"Lancement de la recherche pour : '{query}'", flush=True)
    
    results = retriever.search(query)
    print(f"Nombre de résultats bruts/rerankés retournés : {len(results)}", flush=True)
    
    print(f"\n Résultats pour : '{query}'\n" + "="*50)
    for i, chunk in enumerate(results, 1):
        print(f"\n[Résultat {i}] (Score Rerank: {chunk.score_reranker:.4f})")
        print(f"Source : {chunk.source}")
        print(f"Texte : {chunk.text}...")