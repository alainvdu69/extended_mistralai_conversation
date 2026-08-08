"""Plugin Assist pour Mistral AI (HA 2026.7.2)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.components.conversation import BaseConversationAgent

from .mistral_agent import MistralConversationAgent

_LOGGER = logging.getLogger(__name__)

async def async_get_agent(
    hass: HomeAssistant,
    config: dict[str, Any],
) -> BaseConversationAgent:
    """Crée et retourne l'agent Mistral AI."""
    api_key = config.get("api_key")
    tools_config_path = config.get("tools_config_path", "config/mistral_tools.yaml")
    prompt_path = config.get("prompt_path", "config/mistral_prompt.txt")
    allowed_domains = config.get("allowed_domains", [])
    allowed_services = config.get("allowed_services", {})

    if not api_key:
        raise ValueError("API key for Mistral AI is not configured.")

    return MistralConversationAgent(
        hass=hass,
        api_key=api_key,
        tools_config_path=tools_config_path,
        prompt_path=prompt_path,
        allowed_domains=allowed_domains,
        allowed_services=allowed_services,
    )
