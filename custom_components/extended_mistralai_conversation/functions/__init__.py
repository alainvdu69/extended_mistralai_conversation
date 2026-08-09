"""Registre des exécuteurs de fonctions pour Extended Mistral AI Conversation."""
from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError

from .base import Function
from .composite import CompositeFunction
from .native import NativeFunction
from .script import ScriptFunction
from .template import TemplateFunction
from .web import RestFunction, ScrapeFunction

__all__ = [
    "Function",
    "get_function",
]

FUNCTIONS: dict[str, Function] = {
    "native": NativeFunction(),
    "script": ScriptFunction(),
    "template": TemplateFunction(),
    "rest": RestFunction(),
    "scrape": ScrapeFunction(),
    "composite": CompositeFunction(),
}


def get_function(function_type: str) -> Function:
    """Renvoie l'exécuteur pour un type donné, erreur claire si absent."""
    function = FUNCTIONS.get(function_type)
    if function is None:
        raise HomeAssistantError(
            f"Type de fonction '{function_type}' inconnu (types supportés : {', '.join(FUNCTIONS)})."
        )
    return function
