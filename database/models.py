"""SQLAlchemy models for the Travel Assistant database."""

from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    """Modèle utilisateur pour stocker les informations de compte."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # Pour stocker le mot de passe sécurisé
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": str(self.created_at),
        }


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    summary: Mapped[str] = mapped_column(Text, default="")  # Stocke le résumé mis à jour par le summarizer
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("conversation_sessions.session_id"), index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)  # 'user' ou 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Airport(Base):
    """Airport model representing airport details."""
    __tablename__ = "airports"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)  # IATA code (e.g., 'ALG', 'CDG')
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    terminals: Mapped[str] = mapped_column(String(200), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)
    useful_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self):
        return {
            "code": self.code,
            "name": self.name,
            "city": self.city,
            "country": self.country,
            "terminals": self.terminals,
            "timezone": self.timezone,
            "useful_info": self.useful_info,
        }


class Flight(Base):
    """Flight model for schedule, search, and live flight status."""
    __tablename__ = "flights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flight_number: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    airline: Mapped[str] = mapped_column(String(100), nullable=False)
    origin: Mapped[str] = mapped_column(String(100), nullable=False)  # City or airport name
    origin_code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    departure_time: Mapped[str] = mapped_column(String(10), nullable=False)
    arrival_time: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Live status information
    status: Mapped[str] = mapped_column(String(50), default="Scheduled")  # On Time, Delayed, Cancelled, Landed
    scheduled_departure: Mapped[str] = mapped_column(String(20), nullable=False)
    estimated_departure: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    scheduled_arrival: Mapped[str] = mapped_column(String(20), nullable=False)
    estimated_arrival: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    terminal: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gate: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    price_eur: Mapped[float] = mapped_column(Float, default=150.0)
    available_seats: Mapped[int] = mapped_column(Integer, default=50)

    def to_dict(self):
        return {
            "flight_number": self.flight_number,
            "airline": self.airline,
            "origin": self.origin,
            "origin_code": self.origin_code,
            "destination": self.destination,
            "destination_code": self.destination_code,
            "departure_date": str(self.departure_date),
            "departure_time": self.departure_time,
            "arrival_time": self.arrival_time,
            "status": self.status,
            "scheduled_departure": self.scheduled_departure,
            "estimated_departure": self.estimated_departure or self.scheduled_departure,
            "scheduled_arrival": self.scheduled_arrival,
            "estimated_arrival": self.estimated_arrival or self.scheduled_arrival,
            "terminal": self.terminal,
            "gate": self.gate,
            "price_eur": self.price_eur,
            "available_seats": self.available_seats,
        }


class Booking(Base):
    """Booking model for passenger reservations."""
    __tablename__ = "bookings"

    booking_reference: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g., 'ABC123'
    flight_number: Mapped[str] = mapped_column(String(20), nullable=False)
    flight_date: Mapped[date] = mapped_column(Date, nullable=False)
    passengers: Mapped[str] = mapped_column(String(255), nullable=False)  # Comma-separated names
    travel_class: Mapped[str] = mapped_column(String(50), default="Economy")
    origin: Mapped[str] = mapped_column(String(100), nullable=False)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)
    baggage_allowance: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Confirmed")  # Confirmed, Cancelled

    def to_dict(self):
        return {
            "booking_reference": self.booking_reference,
            "flight_number": self.flight_number,
            "flight_date": str(self.flight_date),
            "passengers": self.passengers,
            "travel_class": self.travel_class,
            "origin": self.origin,
            "destination": self.destination,
            "baggage_allowance": self.baggage_allowance,
            "status": self.status,
        }