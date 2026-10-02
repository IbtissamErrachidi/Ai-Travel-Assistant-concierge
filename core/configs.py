import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# 1. CHARGEMENT OBLIGATOIRE DU FICHIER .ENV
load_dotenv()

# Récupération des variables d'environnement
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct")  # Gardé pour compatibilité des imports

# Configuration pour la démo
if LLM_PROVIDER == "gemini":
    if not GOOGLE_API_KEY or GOOGLE_API_KEY.strip() == "":
        raise ValueError(
            " ERREUR CRITIQUE DÉMO : LLM_PROVIDER est sur 'gemini', mais aucune 'GOOGLE_API_KEY' n'est définie dans le fichier .env !"
    )
    
    # Utilisation de Gemini
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        temperature=0,
        google_api_key=GOOGLE_API_KEY
    )
else:
    # Mode local (Ollama)
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        raise ImportError("Le paquet 'langchain_ollama' est requis pour le mode local.")
    
    llm = ChatOllama(model=LLM_MODEL, temperature=0)