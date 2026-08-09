"""Classe de base pour les exécuteurs de fonctions (adapté de extended_openai_conversation)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError


class Function(ABC):
    """Contrat commun : chaque type ('native', 'script', 'template', 'rest', 'scrape', 'composite')
    implémente execute() et renvoie un résultat (str, dict ou list) que mistral_agent.py
    sérialise ensuite en texte pour le renvoyer à Mistral en tant que réponse de tool_call.
    """

    def validate_entity_ids(
        self,
        hass: HomeAssistant,
        entity_ids: list[str],
        exposed_entities: list[dict[str, Any]],
    ) -> None:
        """Vérifie que les entity_id existent et sont exposées à Assist."""
        not_found = [e for e in entity_ids if hass.states.get(e) is None]
        if not_found:
            raise HomeAssistantError(f"Entité(s) introuvable(s) : {', '.join(not_found)}")

        exposed_entity_ids = {e["entity_id"] for e in exposed_entities}
        not_exposed = [e for e in entity_ids if e not in exposed_entity_ids]
        if not_exposed:
            raise HomeAssistantError(f"Entité(s) non exposée(s) à Assist : {', '.join(not_exposed)}")

    @abstractmethod
    async def execute(
        self,
        hass: HomeAssistant,
        function_config: dict[str, Any],
        arguments: dict[str, Any],
        context: Context | None,
        exposed_entities: list[dict[str, Any]],
    ) -> Any:
        """Exécute la fonction et renvoie son résultat."""
