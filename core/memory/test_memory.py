import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, ConversationSession, ChatMessage
from core.memory.summarizer import ConversationMemorySummarizer  

# Configuration de la base de données
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "database", "travel_assistant.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def test_memory_workflow():
    print("=== DÉBUT DU TEST DE MÉMOIRE ET DU SUMMARIZER ===")
    
    # 1. S'assurer que les tables existent
    Base.metadata.create_all(bind=engine)
    
    session_db = SessionLocal()
    session_id = "test_session_123"
    
    try:
        # 2. Créer ou récupérer la session de conversation
        db_session = session_db.query(ConversationSession).filter(ConversationSession.session_id == session_id).first()
        if not db_session:
            db_session = ConversationSession(session_id=session_id, summary="")
            session_db.add(db_session)
            session_db.commit()
            print(f"-> Session {session_id} créée en base.")
        else:
            print(f"-> Session {session_id} récupérée.")

        # 3. Simuler l'ajout de nouveaux messages (Tours de conversation)
        user_msg = ChatMessage(session_id=session_id, role="user", content="Bonjour, je cherche un vol de Paris vers Alger pour demain.")
        assistant_msg = ChatMessage(session_id=session_id, role="assistant", content="Bonjour ! J'ai trouvé 3 vols disponibles pour Alger au départ de Paris.")
        
        session_db.add(user_msg)
        session_db.add(assistant_msg)
        session_db.commit()
        print("-> Messages simulés ajoutés et enregistrés dans la table chat_messages.")

        # 4. Récupérer l'historique récent pour le summarizer
        recent_messages = session_db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp.asc()).all()
        
        recent_turns_text = "\n".join([f"{msg.role.upper()}: {msg.content}" for msg in recent_messages])
        print(f"\n--- ÉCHANGES RÉCENTS À SYNTHÉTISER ---\n{recent_turns_text}\n--------------------------------------")

        # 5. Tester le Summarizer avec Ollama
        print("-> Appel du ConversationMemorySummarizer (via Ollama)...")
        summarizer = ConversationMemorySummarizer()
        
        existing_summary = db_session.summary or ""
        new_summary = summarizer.update_summary(existing_summary=existing_summary, recent_turns=recent_turns_text)
        
        # Mettre à jour le résumé en base
        db_session.summary = new_summary
        session_db.commit()
        
        print(f"\n[SUCCÈS] Résumé généré et sauvegardé en base :\n--> {new_summary}")

    except Exception as e:
        session_db.rollback()
        print(f"[ERREUR PENDANT LE TEST] : {e}")
    finally:
        session_db.close()
    
    print("=== FIN DU TEST ===")

if __name__ == "__main__":
    test_memory_workflow()