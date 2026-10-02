"""Database initialization script.
Populates SQLite database (travel_assistant.db) with initial test data
covering all challenge scenarios:
- Airports (ALG, CDG, ORY, CMN, DXB)
- Flights (AH1235 [cancelled], AH1009 [terminal info], and search flights for today/tomorrow/next days)
- Bookings (ABC123, XYZ789)
"""

import os
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Airport, Flight, Booking

# Database path inside database directory
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "travel_assistant.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)


def init_database():
    print(f"Creating database tables at: {DB_PATH}")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()

    try:
        # 1. Airports
        airports = [
            Airport(
                code="ALG",
                name="Aéroport d'Alger - Houari Boumediene",
                city="Alger",
                country="Algérie",
                terminals="Terminal 1 (Vols intérieurs), Terminal 4 Ouest (Vols internationaux)",
                timezone="UTC+1 (CET)",
                useful_info="Navette gratuite reliant les terminaux. Wi-Fi gratuit pendant 30 minutes. Salons VIP Première Classe disponibles au Terminal 4.",
            ),
            Airport(
                code="CDG",
                name="Aéroport de Paris-Charles-de-Gaulle",
                city="Paris",
                country="France",
                terminals="Terminal 1, Terminal 2 (2A à 2G), Terminal 3",
                timezone="UTC+1 (CET) / UTC+2 (CEST en été)",
                useful_info="Navette automatique CDGVAL gratuite reliant les terminaux et les gares RER B / TGV. Salons affaires disponibles.",
            ),
            Airport(
                code="ORY",
                name="Aéroport de Paris-Orly",
                city="Paris",
                country="France",
                terminals="Orly 1, Orly 2, Orly 3, Orly 4",
                timezone="UTC+1 (CET) / UTC+2 (CEST en été)",
                useful_info="Relié par la navette Orlyval (station Antony RER B) et le Métro Ligne 14. Départs Air Algérie généralement à Orly 4.",
            ),
            Airport(
                code="CMN",
                name="Aéroport International Mohammed V",
                city="Casablanca",
                country="Maroc",
                terminals="Terminal 1, Terminal 2",
                timezone="UTC+1",
                useful_info="Gare ferroviaire ONCF située au sous-sol du Terminal 1 avec trains réguliers vers Casablanca-Voyageurs.",
            ),
        ]
        session.add_all(airports)

        # 2. Flights
        today = date.today()
        flights = []

        # Generate flights for today and the next 7 days
        for day_offset in range(0, 8):
            current_date = today + timedelta(days=day_offset)

            # Scenario 2 & 5: Flight AH1235 (Cancelled to test refund policy RAG + tool)
            flights.append(
                Flight(
                    flight_number="AH1235",
                    airline="Air Algérie",
                    origin="Paris",
                    origin_code="CDG",
                    destination="Alger",
                    destination_code="ALG",
                    departure_date=current_date,
                    departure_time="10:15",
                    arrival_time="12:35",
                    status="Cancelled",  
                    scheduled_departure="10:15",
                    estimated_departure="Annulé",
                    scheduled_arrival="12:35",
                    estimated_arrival="Annulé",
                    terminal="Terminal 2E",
                    gate="K34",
                    price_eur=180.0,
                    available_seats=0,
                )
            )

            # Scenario 4: Flight AH1009 
            flights.append(
                Flight(
                    flight_number="AH1009",
                    airline="Air Algérie",
                    origin="Paris",
                    origin_code="ORY",
                    destination="Alger",
                    destination_code="ALG",
                    departure_date=current_date,
                    departure_time="14:00",
                    arrival_time="16:20",
                    status="On Time",
                    scheduled_departure="14:00",
                    estimated_departure="14:00",
                    scheduled_arrival="16:20",
                    estimated_arrival="16:20",
                    terminal="Orly 4",  
                    gate="F12",
                    price_eur=165.0,
                    available_seats=28,
                )
            )


            flights.append(
                Flight(
                    flight_number="AH1011",
                    airline="Air Algérie",
                    origin="Paris",
                    origin_code="CDG",
                    destination="Alger",
                    destination_code="ALG",
                    departure_date=current_date,
                    departure_time="18:45",
                    arrival_time="21:05",
                    status="On Time",
                    scheduled_departure="18:45",
                    estimated_departure="18:45",
                    scheduled_arrival="21:05",
                    estimated_arrival="21:05",
                    terminal="Terminal 2E",
                    gate="K42",
                    price_eur=195.0,
                    available_seats=15,
                )
            )

            # Royal Air Maroc Flight
            flights.append(
                Flight(
                    flight_number="AT750",
                    airline="Royal Air Maroc",
                    origin="Casablanca",
                    origin_code="CMN",
                    destination="Paris",
                    destination_code="ORY",
                    departure_date=current_date,
                    departure_time="08:00",
                    arrival_time="12:15",
                    status="On Time",
                    scheduled_departure="08:00",
                    estimated_departure="08:00",
                    scheduled_arrival="12:15",
                    estimated_arrival="12:15",
                    terminal="Terminal 1",
                    gate="B05",
                    price_eur=220.0,
                    available_seats=40,
                )
            )

        session.add_all(flights)

        # 3. Bookings
        # Scenario 4
        bookings = [
            Booking(
                booking_reference="ABC123",
                flight_number="AH1235",
                flight_date=today,
                passengers="Mohamed Alami",
                travel_class="Economy",
                origin="Paris (CDG)",
                destination="Alger (ALG)",
                baggage_allowance="1 bagage en cabine (max 10 kg, 55x35x25 cm) + 1 bagage en soute inclus (max 23 kg)",
                status="Confirmed",
            ),
            Booking(
                booking_reference="XYZ789",
                flight_number="AH1009",
                flight_date=today + timedelta(days=1),
                passengers="Karim Benzema, Sarah Alami",
                travel_class="Business",
                origin="Paris (ORY)",
                destination="Alger (ALG)",
                baggage_allowance="2 bagages en cabine (max 10 kg chacun) + 2 bagages en soute (max 32 kg chacun)",
                status="Confirmed",
            ),
        ]
        session.add_all(bookings)

        session.commit()
        print("Database successfully initialized with initial data!")

    except Exception as e:
        session.rollback()
        print(f"Error initializing database: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    init_database()
