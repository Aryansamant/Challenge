"""Run the two judging scenarios without starting the server."""

from src.engine import BioIntelEngine
from src.models.schemas import ChatRequest


CASES = [
    "Biodiversity is declining on my land",
    """Soil organic carbon: 0.3%
Rainfall: low
Crop: monoculture wheat
Region: semi-arid""",
]


def main() -> None:
    engine = BioIntelEngine()
    for text in CASES:
        print("\n" + "=" * 72)
        print("USER:", text)
        print("-" * 72)
        response = engine.respond(ChatRequest(message=text))
        print(response.assistant_message)


if __name__ == "__main__":
    main()
