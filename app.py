"""
Nedělní čtení s husitským kontextem
====================================
Aplikace poskytuje biblická čtení pro každou neděli
s výkladem v duchu Církve československé husitské (CČSH).

Používá Anthropic Claude API s vlastním systémovým promptem
založeným na Základech víry CČSH.
"""

import os
import json
from datetime import date, timedelta
from pathlib import Path

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


def load_system_prompt() -> str:
    """Načte systémový prompt ze souboru."""
    prompt_path = Path(__file__).parent / "system_prompt.md"
    return prompt_path.read_text(encoding="utf-8")


def load_lectionary() -> dict:
    """Načte lekcionář z JSON souboru."""
    lectionary_path = Path(__file__).parent / "lectionary.json"
    if lectionary_path.exists():
        with open(lectionary_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_next_sunday() -> date:
    """Vrátí datum příští neděle (nebo dnešek, pokud je neděle)."""
    today = date.today()
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0 and today.weekday() == 6:
        return today
    return today + timedelta(days=days_until_sunday or 7)


def get_readings_for_date(target_date: date, lectionary: dict) -> dict | None:
    """Najde čtení pro dané datum v lekcionáři."""
    date_key = target_date.isoformat()
    return lectionary.get(date_key)


def build_user_message(readings: dict) -> str:
    """Sestaví uživatelskou zprávu s biblickými čteními pro AI model."""
    parts = []
    parts.append(f"Neděle: {readings['name']}")

    if readings.get("liturgical_period"):
        parts.append(f"Liturgické období: {readings['liturgical_period']}")

    parts.append("")
    parts.append("Biblická čtení pro tuto neděli:")
    parts.append("")

    for reading in readings.get("readings", []):
        label = reading.get("label", "Čtení")
        reference = reading.get("reference", "")
        text = reading.get("text", "")
        parts.append(f"### {label}: {reference}")
        if text:
            parts.append(text)
        parts.append("")

    parts.append(
        "Prosím, poskytni výklad těchto čtení v duchu "
        "Církve československé husitské."
    )

    return "\n".join(parts)


def generate_context(readings: dict, system_prompt: str) -> str:
    """Vygeneruje husitský kontext k nedělním čtením pomocí Claude API."""
    if Anthropic is None:
        return (
            "Chyba: Knihovna 'anthropic' není nainstalována. "
            "Spusťte: pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return (
            "Chyba: Nastavte proměnnou prostředí ANTHROPIC_API_KEY. "
            "Klíč získáte na https://console.anthropic.com/"
        )

    client = Anthropic(api_key=api_key)
    user_message = build_user_message(readings)

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text


def main():
    """Hlavní funkce aplikace."""
    system_prompt = load_system_prompt()
    lectionary = load_lectionary()

    sunday = get_next_sunday()
    print(f"Nedělní čtení pro: {sunday.strftime('%d. %m. %Y')}")
    print("=" * 50)

    readings = get_readings_for_date(sunday, lectionary)

    if readings is None:
        print(
            f"\nPro datum {sunday.isoformat()} není v lekcionáři "
            f"připraveno čtení."
        )
        print("Zkontrolujte soubor lectionary.json.")
        print("\nMůžete zadat čtení ručně (napište 'konec' pro ukončení):")

        name = input("Název neděle: ").strip()
        if name.lower() == "konec":
            return

        period = input("Liturgické období (volitelné): ").strip()
        reference = input("Biblický odkaz (např. J 3,16-21): ").strip()
        text = input("Text čtení (volitelné, Enter pro přeskočení): ").strip()

        readings = {
            "name": name,
            "liturgical_period": period,
            "readings": [
                {
                    "label": "Čtení",
                    "reference": reference,
                    "text": text,
                }
            ],
        }

    print(f"\n{readings['name']}")
    if readings.get("liturgical_period"):
        print(f"Období: {readings['liturgical_period']}")
    print()

    for reading in readings.get("readings", []):
        print(f"  {reading.get('label', 'Čtení')}: {reading['reference']}")

    print("\n" + "-" * 50)
    print("Generuji husitský kontext...\n")

    context = generate_context(readings, system_prompt)
    print(context)


if __name__ == "__main__":
    main()
