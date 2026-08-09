"""Fonction composite : enchaîne plusieurs fonctions (de n'importe quel type) en séquence.

Le résultat de chaque étape peut être réinjecté dans les arguments de la suivante
via response_variable, exactement comme extended_openai_conversation.
"""
from __future__ import annotations

from typing import Any

from homeassistant.core import Context, HomeAssistant

from .base import Function


class CompositeFunction(Function):
    async def execute(
        self,
        hass: HomeAssistant,
        function_config: dict[str, Any],
        arguments: dict[str, Any],
        context: Context | None,
        exposed_entities: list[dict[str, Any]],
    ) -> Any:
        from . import get_function  # import tardif : évite un import circulaire avec __init__.py

        new_arguments = arguments.copy()
        result = None

        for step_config in function_config["sequence"]:
            step_function = get_function(step_config["type"])
            result = await step_function.execute(hass, step_config, new_arguments, context, exposed_entities)

            response_variable = step_config.get("response_variable")
            if response_variable:
                new_arguments[response_variable] = result

        return result
