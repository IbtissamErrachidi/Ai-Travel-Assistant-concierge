import logging
from core.fallback_agent.fallback_agent import FallbackAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_fallback():
    print("=== TEST DU FALLBACK AGENT ===")
    agent = FallbackAgent()

    class MockRoute:
        def __init__(self, q):
            self.query = q

    class MockResult:
        def __init__(self, needs_clarif, q_clarif=None):
            self.needs_clarification = needs_clarif
            self.clarification_question = q_clarif

    # Test 1 : Salutation
    res1 = agent.generate_response(MockRoute("Bonjour !"), MockResult(False))
    print(f"Test 1 (Salutation) -> {res1.message}")

    # Test 2 : Hors-sujet
    res2 = agent.generate_response(MockRoute("Comment faire une pizza ?"), MockResult(True, "Précisez votre demande de voyage."))
    print(f"Test 2 (Hors-sujet) -> {res2.message}")

if __name__ == "__main__":
    test_fallback()