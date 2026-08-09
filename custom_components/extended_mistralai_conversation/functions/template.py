"""Fonction template : rend un template Jinja2 avec les arguments du tool_call comme variables."""
from __future__ import annotations

from typing import Any

from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers.template import Template

from .base import Function


class TemplateFunction(Function):
    async def execute(
        self,
        hass: HomeAssistant,
        function_config: dict[str, Any],
        arguments: dict[str, Any],
        context: Context | None,
        exposed_entities: list[dict[str, Any]],
    ) -> Any:
        template = Template(function_config["value_template"], hass)
        return template.async_render(
            arguments,
            parse_result=function_config.get("parse_result", False),
        )
