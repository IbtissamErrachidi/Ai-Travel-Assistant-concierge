import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "travel_memory.db")

def init_memory_db():
    """Initialise la base de données SQLite pour la mémoire des conversations."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_memory (
            session_id TEXT PRIMARY KEY,
            summary TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_conversation_summary(session_id: str) -> str:
    """Récupère le résumé de la conversation pour une session donnée."""
    init_memory_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT summary FROM conversation_memory WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""

def save_conversation_summary(session_id: str, summary: str):
    """Enregistre ou met à jour le résumé de la conversation."""
    init_memory_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversation_memory (session_id, summary, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(session_id) 
        DO UPDATE SET summary = excluded.summary, updated_at = CURRENT_TIMESTAMP
    """, (session_id, summary))
    conn.commit()
    conn.close()