"""Unit test script for travel tools."""

import sys
import json


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from tools.flight_tools import (
    search_flights,
    get_flight_status,
    get_airport_info,
    get_booking,
)


def print_test(title: str, result: dict):
    print(f"\n{'='*20} {title} {'='*20}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    print("Testing Travel Assistant Tools against SQLite database...\n")

    # 1. Search flights (Scenario 1)
    res_search = search_flights("Paris", "Alger", "demain")
    print_test("1. search_flights('Paris', 'Alger', 'demain')", res_search)
    assert res_search["status"] == "success", "search_flights failed!"
    assert len(res_search["flights"]) > 0, "No flights found!"

    # 2. Flight status (Scenario 2 & 5: AH1235 is Cancelled)
    res_status = get_flight_status("AH1235", "aujourd'hui")
    print_test("2. get_flight_status('AH1235', 'aujourd\\'hui')", res_status)
    assert res_status["status"] == "success", "get_flight_status failed!"
    assert res_status["flight_status"] == "Cancelled", "Expected AH1235 to be Cancelled!"

    # 3. Flight status with normalization (STT spacing test: 'a h 1 0 0 9')
    res_norm = get_flight_status("a h 1 0 0 9")
    print_test("3. get_flight_status('a h 1 0 0 9') [Normalisation STT]", res_norm)
    assert res_norm["status"] == "success", "Normalization failed!"
    assert res_norm["flight_number"] == "AH1009", "Expected AH1009!"

    # 4. Airport info (Scenario 6)
    res_airport_alg = get_airport_info("ALG")
    print_test("4. get_airport_info('ALG')", res_airport_alg)
    assert res_airport_alg["status"] == "success", "get_airport_info ALG failed!"
    assert "Houari Boumediene" in res_airport_alg["airport"]["name"]

    res_airport_cdg = get_airport_info("CDG")
    print_test("5. get_airport_info('CDG')", res_airport_cdg)
    assert res_airport_cdg["status"] == "success", "get_airport_info CDG failed!"

    # 5. Booking info (Scenario 4)
    res_booking = get_booking("abc 123")  # lowercase with space test
    print_test("6. get_booking('abc 123') [Normalisation PNR]", res_booking)
    assert res_booking["status"] == "success", "get_booking failed!"
    assert res_booking["booking"]["flight_number"] == "AH1235"
    assert "Mohamed Alami" in res_booking["booking"]["passengers"]

    # 6. Negative test (anti-hallucination)
    res_missing_booking = get_booking("NONEXISTENT")
    print_test("7. get_booking('NONEXISTENT') [Anti-hallucination]", res_missing_booking)
    assert res_missing_booking["status"] == "not_found", "Expected not_found for fake booking!"

    print("\n TOUS LES TESTS DES OUTILS ONT RÉUSSI AVEC SUCCÈS !")


if __name__ == "__main__":
    main()
