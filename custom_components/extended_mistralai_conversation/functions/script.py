"""Fonction script : exécute une séquence d'actions HA via le vrai moteur de script.

C'est le point le plus important par rapport à l'ancienne implémentation de
_execute_function : au lieu de rendre "à la main" seulement sequence[0]["data"],
homeassistant.helpers.script.Script exécute la séquence complète (plusieurs
étapes, conditions, templates Jinja natifs) exactement comme le ferait un vrai
script.xxx de Home Assistant.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers.script import Script

from ..const import DOMAIN
from .base import Function

_LOGGER = logging.getLogger(__name__)


class ScriptFunction(Function):
    async def execute(
        self,
        hass: HomeAssistant,
        function_config: dict[str, Any],
        arguments: dict[str, Any],
        context: Context | None,
        exposed_entities: list[dict[str, Any]],
    ) -> Any:
        script = Script(
            hass,
            function_config["sequence"],
            "extended_mistralai_conversation",
            DOMAIN,
            running_description="[extended_mistralai_conversation] function",
            logger=_LOGGER,
        )

        result = await script.async_run(run_variables=arguments, context=context)
        if result is None:
            return "Action réalisée avec succès."
        # Convention déjà en place côté Extended OpenAI Conversation chez vous :
        # un script qui veut renvoyer un message précis au LLM utilise
        # stop: / response_variable pointant vers une clé "_function_result"
        return result.variables.get("_function_result", "Action réalisée avec succès.")
