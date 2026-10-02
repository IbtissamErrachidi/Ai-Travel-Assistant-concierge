from backend.database import SessionLocal
from database.models import Airport, Flight, Booking, User, ConversationSession, ChatMessage

def check_all_database():
    session = SessionLocal()
    
    try:
        users = session.query(User).all()
        print(f"\n================ USERS ({len(users)}) ================")
        for u in users:
            print(f"ID: {u.id} | Nom: {u.name} | Email: {u.email} | Hash: {u.password_hash}")

        airports = session.query(Airport).all()
        print(f"\n================ AIRPORTS ({len(airports)}) ================")
        for a in airports:
            print(f"[{a.code}] {a.name} ({a.city}, {a.country}) - Terminaux: {a.terminals}")

        flights = session.query(Flight).all()
        print(f"\n================ FLIGHTS ({len(flights)}) ================")
        for f in flights:
            print(f"Vol {f.flight_number} | {f.airline} | {f.origin_code} ➔ {f.destination_code} | Date: {f.departure_date} | Statut: {f.status} | Prix: {f.price_eur}€")

        bookings = session.query(Booking).all()
        print(f"\n================ BOOKINGS ({len(bookings)}) ================")
        for b in bookings:
            pass_name = getattr(b, 'passenger', getattr(b, 'passagers', 'N/A'))
            print(f"Ref: {b.booking_reference} | Vol: {b.flight_number} | Passager: {pass_name} | Classe: {b.travel_class} | Statut: {b.status}")

        all_sessions = session.query(ConversationSession).all()
        print(f"\n================ CONVERSATION SESSIONS ({len(all_sessions)}) ================")
        for s in all_sessions:
            print(f"Session ID: {s.session_id}")
            print(f"Résumé persistant: {s.summary if s.summary else '(Aucun résumé)'}")
            print(f"Dernière mise à jour: {s.updated_at}")
            print("-" * 40)

        all_messages = session.query(ChatMessage).order_by(ChatMessage.timestamp.asc()).all()
        print(f"\n================ CHAT MESSAGES ({len(all_messages)}) ================")
        for m in all_messages:
            print(f"[{m.timestamp}] Session: {m.session_id[:8]}... | {m.role.upper()}: {m.content}")

    except Exception as e:
        print(f"Erreur lors de la lecture de la base de données : {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_all_database()