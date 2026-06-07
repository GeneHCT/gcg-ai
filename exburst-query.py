import json
from pathlib import Path
from typing import Any

import requests

from simulator.card_data import DEFAULT_NORMALIZED_CARDS_PATH, write_normalized_card_database

URL = "https://auth.exburst.dev/rest/v1/gundam_cards"
OUTPUT_PATH = Path("exburst_cards.json")
NORMALIZED_OUTPUT_PATH = DEFAULT_NORMALIZED_CARDS_PATH
BATCH_SIZE = 1000
REQUEST_TIMEOUT_SECONDS = 30

HEADERS = {
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0Zmtkbml3YnZ5b2F5cGp2dWxwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNzQwMzUsImV4cCI6MjA2Mzk1MDAzNX0.iCCIOIt8durZJg2JtSCBhPuza7j3pFfF8mS_Xj1m7Ic",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0Zmtkbml3YnZ5b2F5cGp2dWxwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNzQwMzUsImV4cCI6MjA2Mzk1MDAzNX0.iCCIOIt8durZJg2JtSCBhPuza7j3pFfF8mS_Xj1m7Ic",
    "Content-Type": "application/json",
}


def fetch_cards() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    offset = 0

    while True:
        params = {
            "select": "cardno,name,color,level,cost,apdata,hp,effectdata,trait,link,originalid,published",
            "published": "eq.1",
            "limit": BATCH_SIZE,
            "offset": offset,
        }
        response = requests.get(
            URL,
            headers=HEADERS,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        batch = response.json()
        if not batch:
            break

        cards.extend(batch)
        print(f"Fetched {len(cards)} cards so far...")

        if len(batch) < BATCH_SIZE:
            break
        offset += BATCH_SIZE

    return cards


def main() -> None:
    try:
        cards = fetch_cards()
    except requests.RequestException as error:
        print(f"API request failed: {error}")
        return

    OUTPUT_PATH.write_text(json.dumps(cards, indent=2), encoding="utf-8")
    print(f"Saved {len(cards)} published cards to {OUTPUT_PATH}")
    normalized_cards = write_normalized_card_database(OUTPUT_PATH, NORMALIZED_OUTPUT_PATH)
    print(f"Saved {len(normalized_cards)} normalized cards to {NORMALIZED_OUTPUT_PATH}")


if __name__ == "__main__":
    main()