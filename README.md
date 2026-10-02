# AI Travel Assistant ✈️

> Conciergerie aérienne intelligente combinant RAG, Tool Calling et saisie vocale multilingue — propulsée par LangGraph et un LLM configurable (Qwen via Ollama ou Gemini).

---

## Fonctionnalités clés

- **RAG (Retrieval-Augmented Generation)** — Recherche sémantique sur les documents officiels Royal Air Maroc via Qdrant
- **Tool Calling** — Interrogation en temps réel des vols, statuts et disponibilités via des outils structurés
- **Routage hybride RAG + Outils** — Le planner LangGraph décide dynamiquement quelle stratégie utiliser selon la requête
- **Saisie vocale multilingue** — Transcription audio via Faster-Whisper + détection de parole Silero VAD
- **Interface moderne** — Chat SSE avec streaming token-par-token, design Royal Air Maroc, sans jargon technique

---

## Stack technique

| Couche | Technologies |
|---|---|
| **LLM (Configurable)** | **Qwen** (en local via Ollama) ou **Gemini** (via `.env`) |
| **Orchestration** | LangGraph (graphe d'agents stateful) |
| **RAG / Embeddings** | Qdrant · FastEmbed · `sentence-transformers` |
| **Speech-to-Text** | Faster-Whisper · Silero VAD · PyAV |
| **Backend** | FastAPI · SQLAlchemy · SQLite |
| **Frontend** | HTML/CSS/JS vanilla · SSE (Server-Sent Events) |
| **Ingestion PDF** | pdfplumber |
| **Auth** | JWT (`python-jose`) · bcrypt · passlib |
| **Runtime** | Python 3.13 · uv |

---

## Architecture


```

Challenge_technique_Travel_Assistant/
│
├── backend/            # FastAPI app (routes, SSE, auth, transcription)
├── core/
│   ├── graph/          # LangGraph workflow + prompts
│   ├── planner/        # Planner agent + prompt de routage
│   ├── memory/         # ConversationMemorySummarizer (résumé tous les 20 msgs)
│   └── fallback_agent/ # Agent de secours hors-domaine
│
├── tools/              # Outils de vol (statut, disponibilité, prix)
├── rag/                # Pipeline RAG (retriever, Qdrant)
├── ingestion/          # Pipeline d'ingestion (extract, clean, chunking, embedder)
├── rag_data/           # Dossier contenant les documents PDF sources à ingérer
├── speech/             # SpeechToText (Whisper + VAD)
├── database/           # Modèles SQLAlchemy, initialisation (`init_db.py`) et vérification (`check_db.py`)
├── frontend/           # Interface HTML/CSS/JS
│
├── docker-compose.yml  # Qdrant en container (Dashboard sur le port 16333)
├── run_server.py       # Point d'entrée du serveur
└── pyproject.toml

```

---

## Installation & Quickstart

**Prérequis** : Python 3.13+, [uv](https://docs.astral.sh/uv/), Docker

```bash
# 1. Cloner le projet
git clone <repo-url>
cd Challenge_technique_Travel_Assistant

# 2. Installer les dépendances
uv sync

# 3. Configurer les variables d'environnement dans le fichier .env
# Exemple de configuration :
# GOOGLE_API_KEY=votre_cle_api_gemini
# LLM_PROVIDER=ollama   # (ou gemini)

# 4. Lancer Qdrant (Base vectorielle via Docker sur le port 16333)
# Dashboard accessible sur http://localhost:16333/dashboard#/collections
docker-compose up -d

# 5. Initialiser la Base de Données SQLite (Aéroports, Vols, Réservations)
uv run python database/init_db.py

# (Optionnel) Vérifier le contenu de la base de données via le script de test
uv run python database/check_db.py

# 6. Exécuter le pipeline d'ingestion des documents RAG fichier par fichier :
uv run python ingestion/extract.py     # Étape 1 : Extraction du texte des PDF
uv run python ingestion/clean.py       # Étape 2 : Nettoyage du texte extrait
uv run python ingestion/chunking.py    # Étape 3 : Découpage en morceaux (chunks)
uv run python ingestion/embedder.py    # Étape 4 : Vectorisation et stockage dans Qdrant
# 7. Démarrer le serveur de l'application
uv run python run_server.py

```

> Application disponible sur **http://localhost:8000** (Utilisateur démo pré-créé : `ibtissam.errachidi@travel.ai` / `demo1234`)

---

## 🤝 Contribuer

Les contributions, issues et demandes de fonctionnalités sont les bienvenues ! N'hésitez pas à consulter la [page des issues](https://github.com/yourusername/ensaj_assistant/issues).

---

## 📝 Licence

Ce projet est distribué sous licence MIT.