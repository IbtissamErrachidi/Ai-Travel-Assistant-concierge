"""
FastAPI Backend — AI Travel Assistant
Endpoints:
  POST /api/auth/login      → authenticate user, return JWT
  GET  /api/auth/me         → get current user profile
  POST /api/chat            → send a message, get AI response
  GET  /api/chat/history    → get conversation history for current session
  POST /api/auth/register   → create account (dev/demo only)
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import hash_password, verify_password, create_access_token, decode_access_token
from backend.database import get_db, init_db
from database.models import User, ConversationSession, ChatMessage
from core.graph.workflow import app as langgraph_app

import os

# Créer un dossier logs à la racine s'il n'existe pas
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        # Enregistre tous les logs dans un fichier .log
        logging.FileHandler("logs/travel_assistant.log", encoding="utf-8"),
        # Affiche aussi les logs dans la console du terminal
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TravelAssistantAPI")

# ──────────────────────────────────────────────
# App setup
# ──────────────────────────────────────────────

app = FastAPI(title="AI Travel Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ──────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: list = []
    message_count: int = 0


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expiré")
    user = db.query(User).filter(User.email == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable")
    return user


def get_or_create_session(session_id: Optional[str], db: Session) -> ConversationSession:
    """Return an existing ConversationSession or create a new one."""
    if session_id:
        session = db.query(ConversationSession).filter(
            ConversationSession.session_id == session_id
        ).first()
        if session:
            return session
    # Create new session
    new_id = session_id or str(uuid.uuid4())
    session = ConversationSession(session_id=new_id, summary="")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def build_chat_history(session_id: str, db: Session, max_turns: int = 10) -> str:
    """Return the last N message pairs as a formatted string for the planner and synthesizer."""
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(max_turns * 2)
        .all()
    )
    messages = list(reversed(messages))
    lines = []
    for m in messages:
        role_label = "Utilisateur" if m.role == "user" else "Assistant"
        lines.append(f"{role_label}: {m.content}")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# Startup
# ──────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialized.")
    # Seed demo user if not present
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        demo = db.query(User).filter(User.email == "ibtissam.errachidi@travel.ai").first()
        if not demo:
            demo = User(
                name="Ibtissam Er-Rachidi",
                email="ibtissam.errachidi@travel.ai",
                password_hash=hash_password("demo1234"),
            )
            db.add(demo)
            db.commit()
            logger.info("Utilisateur de démo créé : ibtissam.errachidi@travel.ai / demo1234")
    finally:
        db.close()


# ──────────────────────────────────────────────
# Auth routes
# ──────────────────────────────────────────────

@app.post("/api/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Email ou mot de passe incorrect")
    token = create_access_token({"sub": user.email})
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "name": user.name, "email": user.email},
    )


@app.post("/api/auth/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    user = User(name=req.name, email=req.email, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.email})
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "name": user.name, "email": user.email},
    )


@app.get("/api/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return current_user.to_dict()


# ──────────────────────────────────────────────
# Chat routes
# ──────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a user message through the LangGraph workflow and return the AI response."""

    # 1. Get or create session
    conv_session = get_or_create_session(req.session_id, db)
    session_id = conv_session.session_id

    # 2. Count messages in this session (to track 20-message milestone)
    message_count = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .count()
    )

    # 3. Build chat history string for the planner
    chat_history = build_chat_history(session_id, db)

    # 4. Save user message to DB
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=req.message,
        timestamp=datetime.utcnow(),
    )
    db.add(user_msg)
    db.commit()

    # 5. Run LangGraph workflow
    initial_state = {
        "session_id": session_id,
        "user_query": req.message,
        "chat_history": chat_history,
        "conversation_summary": conv_session.summary or "",
        "message_count": message_count,
        "plan": [],
        "needs_clarification": False,
        "clarification_question": None,
        "retrieved_chunks": [],
        "tool_results": [],
        "synthesis_context": "",
        "final_answer": "",
        "final_response": "",
        "sources": [],
    }

    try:
        final_state = await langgraph_app.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"LangGraph error: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur du workflow IA : {str(e)}")

    answer = final_state.get("final_answer") or final_state.get("final_response", "Désolé, je n'ai pas pu traiter votre demande.")
    sources = final_state.get("sources", [])
    new_message_count = final_state.get("message_count", message_count + 1)

    # 6. Update conversation summary if it was refreshed
    updated_summary = final_state.get("conversation_summary", "")
    if updated_summary != conv_session.summary:
        conv_session.summary = updated_summary
        conv_session.updated_at = datetime.utcnow()
        db.commit()

    # 7. Save assistant response to DB
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer,
        timestamp=datetime.utcnow(),
    )
    db.add(assistant_msg)
    db.commit()

    return ChatResponse(
        answer=answer,
        session_id=session_id,
        sources=sources,
        message_count=new_message_count,
    )


@app.post("/api/chat/stream")
async def chat_stream(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    SSE endpoint: runs the LangGraph workflow, then streams the final answer
    token-by-token so the frontend can display text progressively.
    Each SSE event is a JSON object: {"type": "token"|"done"|"meta", ...}
    """

    # ── session & history ──────────────────────────────────────────────
    conv_session = get_or_create_session(req.session_id, db)
    session_id = conv_session.session_id

    message_count = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .count()
    )
    chat_history = build_chat_history(session_id, db)

    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=req.message,
        timestamp=datetime.utcnow(),
    )
    db.add(user_msg)
    db.commit()

    initial_state = {
        "session_id": session_id,
        "user_query": req.message,
        "chat_history": chat_history,
        "conversation_summary": conv_session.summary or "",
        "message_count": message_count,
        "plan": [],
        "needs_clarification": False,
        "clarification_question": None,
        "retrieved_chunks": [],
        "tool_results": [],
        "synthesis_context": "",
        "final_answer": "",
        "final_response": "",
        "sources": [],
    }

    async def event_generator() -> AsyncGenerator[str, None]:
        # ── 1. Emit natural initial status ──────────────────────────────────
        yield f"data: {json.dumps({'type': 'status', 'message': 'Recherche des informations en cours...'})}\n\n"
        await asyncio.sleep(0.02)

        # ── 2. Run the graph ────────────────────────────────────────────────
        try:
            final_state = await langgraph_app.ainvoke(initial_state)
        except Exception as e:
            logger.error(f"LangGraph stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        answer = (
            final_state.get("final_answer")
            or final_state.get("final_response", "")
            or "Désolé, je n'ai pas pu traiter votre demande."
        )
        sources = final_state.get("sources", [])
        new_count = final_state.get("message_count", message_count + 1)

        # ── 3. Persist answer & update summary ────────────────────────────────
        updated_summary = final_state.get("conversation_summary", "")
        if updated_summary != conv_session.summary:
            conv_session.summary = updated_summary
            conv_session.updated_at = datetime.utcnow()
            db.commit()

        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=answer,
            timestamp=datetime.utcnow(),
        )
        db.add(assistant_msg)
        db.commit()

        # Emit brief transition status before streaming tokens
        yield f"data: {json.dumps({'type': 'status', 'message': 'Préparation de votre réponse...'})}\n\n"
        await asyncio.sleep(0.03)

        # ── 4. Stream tokens word-by-word for real-time progressive display ───
        words = answer.split(" ")
        for i, word in enumerate(words):
            token = word if i == 0 else " " + word
            yield f"data: {json.dumps({'type': 'token', 'value': token})}\n\n"
            await asyncio.sleep(0.015)   # ~65 words/sec — very smooth & natural reading pace

        # ── 5. Send completion event with sources and session id ──────────────
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'sources': sources, 'message_count': new_count})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/chat/history")
def chat_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the full conversation history for a session."""
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
        .all()
    )
    return [
        {
            "role": m.role,
            "content": m.content,
            "timestamp": str(m.timestamp),
        }
        for m in messages
    ]


@app.get("/api/sessions")
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all sessions that have messages (for sidebar history)."""
    sessions = (
        db.query(ChatMessage.session_id)
        .distinct()
        .all()
    )
    result = []
    for (sid,) in sessions:
        first_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == sid, ChatMessage.role == "user")
            .order_by(ChatMessage.timestamp.desc()) # 👈 Récupérer le message le plus récent de la session
            .first()
        )
        if first_msg:
            result.append({
                "session_id": sid,
                "title": first_msg.content[:60],
                "date": str(first_msg.timestamp.date()),
                "timestamp": first_msg.timestamp # Pour pouvoir trier globalement
            })
    
    result.sort(key=lambda x: x["timestamp"], reverse=True)
    return result



@app.delete("/api/sessions/{session_id}")
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Supprime une session de conversation et tous ses messages."""
    # Supprimer les messages de la session
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    # Supprimer la session elle-même
    session = db.query(ConversationSession).filter(ConversationSession.session_id == session_id).first()
    if session:
        db.delete(session)
    db.commit()
    return {"status": "success", "message": "Session supprimée avec succès"}


# ──────────────────────────────────────────────
# Audio transcription route
# ──────────────────────────────────────────────

@app.post("/api/audio/transcribe")
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint de transcription audio :
    Reçoit un fichier audio du front-end, le transmet à Silero VAD + Whisper,
    normalise les codes de vol et renvoie le texte transcrit.
    """
    from speech.speech_to_text import transcribe_audio_file

    if not file:
        raise HTTPException(status_code=400, detail="Aucun fichier audio fourni.")

    ext = os.path.splitext(file.filename or "")[1] or ".webm"
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"audio_{uuid.uuid4()}{ext}")

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # Exécution de Whisper + VAD dans un thread dédié
        transcribed_text = await asyncio.to_thread(transcribe_audio_file, temp_path)
        return {"text": transcribed_text or ""}
    except Exception as e:
        logger.error(f"Erreur lors de la transcription audio : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur de transcription audio : {str(e)}")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ──────────────────────────────────────────────
# Serve frontend static files
# ──────────────────────────────────────────────

import os as _os
_frontend_dir = _os.path.join(_os.path.dirname(__file__), "..", "frontend")

app.mount("/static", StaticFiles(directory=_frontend_dir), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(_os.path.join(_frontend_dir, "index.html"))
