"""Dynamic tools for Travel Assistant connected to SQLite database.
Contains the 4 core tools:
1. search_flights(origin, destination, departure_date)
2. get_flight_status(flight_number, date)
3. get_airport_info(airport_code)
4. get_booking(booking_reference)
"""

import os
import re
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, or_, and_
from sqlalchemy.orm import sessionmaker

from database.models import Airport, Flight, Booking

# Database configuration
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "travel_assistant.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def _clean_code(value: Optional[str]) -> str:
    """Normalize flight numbers, booking references, and airport codes.
    Removes spaces and converts to uppercase (e.g., 'ah 1235' -> 'AH1235').
    """
    if not value:
        return ""
    return re.sub(r"\s+", "", value).upper()


def _parse_date(date_input: Optional[Any]) -> Optional[date]:
    """Parse flexible date inputs:
    - None -> today
    - 'aujourd\'hui', 'today' -> today
    - 'demain', 'tomorrow' -> tomorrow
    - 'après-demain', 'apres-demain' -> day after tomorrow
    - Jours de la semaine ('vendredi', 'friday', etc.) -> calcul du prochain jour correspondant
    - 'YYYY-MM-DD' ou 'DD/MM/YYYY' -> date object
    """
    if not date_input:
        return date.today()
    
    if isinstance(date_input, date):
        return date_input

    # Nettoyage immédiat de la chaîne
    clean_str = str(date_input).strip().lower()
    today = date.today()

    # 1. PRIORITÉ ABSOLUE AUX FORMATS CHIFFRÉS (Évite toute confusion avec les termes relatifs)
    try:
        return datetime.strptime(clean_str, "%Y-%m-%d").date()
    except ValueError:
        pass

    try:
        return datetime.strptime(clean_str, "%d/%m/%Y").date()
    except ValueError:
        pass

    # 2. Dates relatives
    if clean_str in ["aujourd'hui", "aujourdhui", "today", "ce jour"]:
        return today
    elif clean_str in ["demain", "tomorrow"]:
        return today + timedelta(days=1)
    elif clean_str in ["après-demain", "apres-demain", "apres demain", "day after tomorrow"]:
        return today + timedelta(days=2)

    # 3. Jours de la semaine (Français et Anglais)
    weekdays = {
        "lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6,
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
    }

    if clean_str in weekdays:
        target_weekday = weekdays[clean_str]
        days_ahead = (target_weekday - today.weekday()) % 7
        # Si c'est aujourd'hui même, on vise le prochain
        if days_ahead == 0:
            days_ahead = 7
        return today + timedelta(days=days_ahead)

    # Default fallback to today if unparsed
    return today

def search_flights(origin: str, destination: str, departure_date: Optional[str] = None) -> Dict[str, Any]:
    """Recherche les vols disponibles entre une ville/aéroport de départ et une ville/aéroport d'arrivée pour une date donnée.

    Args:
        origin (str): Ville ou code IATA de départ (ex: 'Paris', 'CDG', 'ORY').
        destination (str): Ville ou code IATA de destination (ex: 'Alger', 'ALG').
        departure_date (Optional[str]): Date de départ ('YYYY-MM-DD', 'demain', 'vendredi', etc.).

    Returns:
        Dict[str, Any]: Liste des vols disponibles avec horaires, prix et places disponibles.
    """
    target_date = _parse_date(departure_date)
    orig_clean = origin.strip()
    dest_clean = destination.strip()

    session = SessionLocal()
    try:
        query = session.query(Flight).filter(
            and_(
                or_(
                    Flight.origin.ilike(f"%{orig_clean}%"),
                    Flight.origin_code.ilike(orig_clean),
                ),
                or_(
                    Flight.destination.ilike(f"%{dest_clean}%"),
                    Flight.destination_code.ilike(dest_clean),
                ),
                Flight.departure_date == target_date,
            )
        )
        flights = query.all()

        if not flights:
            return {
                "status": "not_found",
                "message": (
                    f"Aucun vol disponible trouvé entre '{origin}' et '{destination}' "
                    f"pour la date du {target_date.strftime('%d/%m/%Y')}."
                ),
                "flights": [],
            }

        return {
            "status": "success",
            "count": len(flights),
            "date": str(target_date),
            "flights": [f.to_dict() for f in flights],
        }

    except Exception as e:
        return {"status": "error", "message": f"Erreur lors de la recherche de vols : {str(e)}"}
    finally:
        session.close()


def get_flight_status(flight_number: str, date: Optional[str] = None) -> Dict[str, Any]:
    """Obtient le statut en temps réel d'un vol (statut, heure prévue, heure estimée, terminal, porte).

    Args:
        flight_number (str): Numéro de vol (ex: 'AH1235', 'AH1009', 'AT750').
        date (Optional[str]): Date du vol ('YYYY-MM-DD', 'aujourd\'hui', 'demain'). Si omis, la date du jour est utilisée.

    Returns:
        Dict[str, Any]: Informations détaillées sur le statut du vol.
    """
    clean_number = _clean_code(flight_number)
    target_date = _parse_date(date)

    session = SessionLocal()
    try:
        flight = session.query(Flight).filter(
            Flight.flight_number == clean_number,
            Flight.departure_date == target_date,
        ).first()

        if not flight:
            flight = session.query(Flight).filter(
                Flight.flight_number == clean_number
            ).order_by(Flight.departure_date.desc()).first()

        if not flight:
            return {
                "status": "not_found",
                "message": (
                    f"Le vol {clean_number} n'a pas été trouvé dans notre système pour le "
                    f"{target_date.strftime('%d/%m/%Y')}."
                ),
            }

        return {
            "status": "success",
            "flight_number": flight.flight_number,
            "airline": flight.airline,
            "origin": f"{flight.origin} ({flight.origin_code})",
            "destination": f"{flight.destination} ({flight.destination_code})",
            "departure_date": str(flight.departure_date),
            "flight_status": flight.status,
            "scheduled_departure": flight.scheduled_departure,
            "estimated_departure": flight.estimated_departure or flight.scheduled_departure,
            "scheduled_arrival": flight.scheduled_arrival,
            "estimated_arrival": flight.estimated_arrival or flight.scheduled_arrival,
            "terminal": flight.terminal or "Non précisé",
            "gate": flight.gate or "Non précisée",
        }

    except Exception as e:
        return {"status": "error", "message": f"Erreur lors de la récupération du statut : {str(e)}"}
    finally:
        session.close()


def get_airport_info(airport_code: str) -> Dict[str, Any]:
    """Obtient les informations détaillées sur un aéroport."""
    clean_code = _clean_code(airport_code)
    raw_query = airport_code.strip()

    session = SessionLocal()
    try:
        airport = session.query(Airport).filter(
            or_(
                Airport.code == clean_code,
                Airport.city.ilike(f"%{raw_query}%"),
                Airport.name.ilike(f"%{raw_query}%"),
            )
        ).first()

        if not airport:
            return {
                "status": "not_found",
                "message": f"Aucun aéroport trouvé pour la recherche '{airport_code}'.",
            }

        return {
            "status": "success",
            "airport": airport.to_dict(),
        }

    except Exception as e:
        return {"status": "error", "message": f"Erreur lors de la récupération des informations aéroport : {str(e)}"}
    finally:
        session.close()


def get_booking(booking_reference: str) -> Dict[str, Any]:
    """Récupère les informations détaillées d'une réservation à partir de sa référence (PNR)."""
    clean_ref = _clean_code(booking_reference)

    session = SessionLocal()
    try:
        booking = session.query(Booking).filter(
            Booking.booking_reference == clean_ref
        ).first()

        if not booking:
            return {
                "status": "not_found",
                "message": f"Aucune réservation trouvée pour la référence '{clean_ref}'.",
            }

        return {
            "status": "success",
            "booking": booking.to_dict(),
        }

    except Exception as e:
        return {"status": "error", "message": f"Erreur lors de la récupération de la réservation : {str(e)}"}
    finally:
        session.close()