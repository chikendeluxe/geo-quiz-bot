"""
Génération des questions pour les trois types de quiz :
  • flag     – Identifier le pays à partir d'un drapeau emoji
  • capital  – Capitale → pays OU pays → capitale (tirage aléatoire)
  • map      – Identifier le pays colorié sur la carte
"""

import random
from countries_data import COUNTRIES, get_flag

# ── Helpers ──────────────────────────────────────────────────────────────────

def get_pool(difficulty: str) -> list[dict]:
    """Retourne la liste de pays selon la difficulté choisie."""
    if difficulty == "all":
        return COUNTRIES.copy()
    pool = [c for c in COUNTRIES if c["difficulty"] == difficulty]
    # Fallback si le pool est trop petit (< 8 pays)
    return pool if len(pool) >= 8 else COUNTRIES.copy()


def pick_distractors(correct: dict, pool: list[dict], n: int = 3) -> list[dict]:
    """
    Sélectionne n mauvaises réponses.
    Favorise le même continent pour plus de challenge.
    """
    others = [c for c in pool if c["fr"] != correct["fr"]]
    same   = [c for c in others if c["continent"] == correct["continent"]]
    diff   = [c for c in others if c["continent"] != correct["continent"]]

    chosen: list[dict] = []
    # Tente de mettre 2 voisins du même continent
    if len(same) >= 2:
        chosen = random.sample(same, min(2, n))
        remaining_n = n - len(chosen)
        fill_pool = diff if len(diff) >= remaining_n else others
        if len(fill_pool) >= remaining_n:
            chosen += random.sample(fill_pool, remaining_n)
    else:
        chosen = random.sample(others, min(n, len(others)))

    return chosen[:n]


def shuffle_choices(*args: str) -> list[str]:
    """Mélange les choix (bonne réponse + distracteurs)."""
    lst = list(args)
    random.shuffle(lst)
    return lst


# ── Créateurs de questions ────────────────────────────────────────────────────

def make_flag_question(country: dict, pool: list[dict]) -> dict:
    flag = get_flag(country["iso2"])
    distractors = pick_distractors(country, pool)
    choices = shuffle_choices(country["fr"], *[d["fr"] for d in distractors])
    return {
        "type":       "flag",
        "flag_emoji": flag,
        "answer":     country["fr"],
        "choices":    choices,
        "country_en": country["en"],
        "country_fr": country["fr"],
    }


def make_capital_question(country: dict, pool: list[dict]) -> dict:
    variant = random.choice(["country_to_capital", "capital_to_country"])
    distractors = pick_distractors(country, pool)

    if variant == "country_to_capital":
        # Quelle est la capitale de X ?  →  choix : capitales
        choices = shuffle_choices(
            country["capital_fr"],
            *[d["capital_fr"] for d in distractors],
        )
        return {
            "type":       "capital",
            "text":       f"🏛️ Quelle est la capitale de **{country['fr']}** ?",
            "answer":     country["capital_fr"],
            "choices":    choices,
            "country_en": country["en"],
            "country_fr": country["fr"],
        }
    else:
        # Y est la capitale de quel pays ?  →  choix : noms de pays
        choices = shuffle_choices(
            country["fr"],
            *[d["fr"] for d in distractors],
        )
        return {
            "type":       "capital",
            "text":       f"🏛️ **{country['capital_fr']}** est la capitale de quel pays ?",
            "answer":     country["fr"],
            "choices":    choices,
            "country_en": country["en"],
            "country_fr": country["fr"],
        }


def make_map_question(country: dict, pool: list[dict]) -> dict:
    distractors = pick_distractors(country, pool)
    choices = shuffle_choices(country["fr"], *[d["fr"] for d in distractors])
    return {
        "type":       "map",
        "text":       "🗺️ Quel est le pays colorié en **rouge** sur cette carte ?",
        "answer":     country["fr"],
        "choices":    choices,
        "country_en": country["en"],
        "country_fr": country["fr"],
    }


# ── Générateur principal ──────────────────────────────────────────────────────

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
    """
    Génère une liste de questions.

    Args:
        question_types : sous-ensemble de ['flag', 'capital', 'map']
        difficulty     : 'easy' | 'medium' | 'hard' | 'all'
        num_questions  : nombre total de questions (5-20)
    """
    pool = get_pool(difficulty)

    # Pool de pays disponibles – on évite les répétitions
    available = pool.copy()
    random.shuffle(available)

    # Cycle des types
    type_cycle = question_types * (num_questions // len(question_types) + 1)
    random.shuffle(type_cycle)

    questions: list[dict] = []

    for i in range(num_questions):
        if not available:
            available = pool.copy()
            random.shuffle(available)

        country  = available.pop(0)
        q_type   = type_cycle[i % len(type_cycle)]
        maker    = _MAKERS.get(q_type, make_flag_question)
        questions.append(maker(country, pool))

    return questions
