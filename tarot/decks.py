"""Deck visibility affects new choices, never historical shoe membership."""


def available_decks(registry: dict) -> dict:
    return {key: spec for key, spec in registry["decks"].items() if spec.get("selectable", True)}


def default_deck(registry: dict) -> str:
    choices = available_decks(registry)
    chosen = registry.get("default_deck")
    if not choices:
        raise ValueError("Registry needs at least one selectable deck")
    if chosen is not None and chosen not in choices:
        raise ValueError("Default deck must be selectable")
    return chosen or next(iter(choices))
