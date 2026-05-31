"""
Génération des questions pour les trois types de quiz.
Pas de QCM — les joueurs tapent leur réponse.
"""

import random
from countries_data import COUNTRIES, get_flag


def get_pool(difficulty: str) -> list[dict]:
    if difficulty == "all":
        return COUNTRIES.copy()
    pool = [c for c in COUNTRIES if c["difficulty"] == difficulty]
    return pool if len(pool) >= 8 else COUNTRIES.copy()


def pick_distractors(correct: dict, pool: list[dict], n: int = 3) -> list[dict]:
    others = [c for c in pool if c["fr"] != correct["fr"]]
    same   = [c for c in others if c["continent"] == correct["continent"]]
    diff   = [c for c in others if c["continent"] != correct["continent"]]

    chosen: list[dict] = []
    if len(same) >= 2:
        chosen = random.sample(same, min(2, n))
        remaining_n = n - len(chosen)
        fill_pool = diff if len(diff) >= remaining_n else others
        if len(fill_pool) >= remaining_n:
            chosen += random.sample(fill_pool, remaining_n)
    else:
        chosen = random.sample(others, min(n, len(others)))

    return chosen[:n]


def make_flag_question(country: dict, pool: list[dict]) -> dict:
    return {
        "type":       "flag",
        "answer":     country["fr"],
        "iso2":       country["iso2"],   # pour l'image flagcdn.com
        "country_en": country["en"],
        "country_fr": country["fr"],
    }


def make_capital_question(country: dict, pool: list[dict]) -> dict:
    variant = random.choice(["country_to_capital", "capital_to_country"])

    if variant == "country_to_capital":
        return {
            "type":       "capital",
            "text":       f"🏛️ Quelle est la capitale de **{country['fr']}** ?",
            "answer":     country["capital_fr"],
            "country_en": country["en"],
            "country_fr": country["fr"],
        }
    else:
        return {
            "type":       "capital",
            "text":       f"🏛️ **{country['capital_fr']}** est la capitale de quel pays ?",
            "answer":     country["fr"],
            "country_en": country["en"],
            "country_fr": country["fr"],
        }


def make_map_question(country: dict, pool: list[dict]) -> dict:
    return {
        "type":       "map",
        "text":       "🗺️ Quel est le pays colorié en **rouge** sur cette carte ?",
        "answer":     country["fr"],
        "country_en": country["en"],
        "country_fr": country["fr"],
    }


_MAKERS = {
    "flag":    make_flag_question,
    "capital": make_capital_question,
    "map":     make_map_question,
}


def generate_questions(
    question_types: list[str],
    difficulty: str,
    num_questions: int,
) -> list[dict]:
    pool      = get_pool(difficulty)
    available = pool.copy()
    random.shuffle(available)

    type_cycle = question_types * (num_questions // len(question_types) + 1)
    random.shuffle(type_cycle)

    questions: list[dict] = []

    for i in range(num_questions):
        if not available:
            available = pool.copy()
            random.shuffle(available)

        country = available.pop(0)
        q_type  = type_cycle[i % len(type_cycle)]
        questions.append(_MAKERS.get(q_type, make_flag_question)(country, pool))

    return questions
