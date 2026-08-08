"""Conversation platform for Mistral AI."""
from __future__ import annotations

import logging

from homeassistant.components.conversation import ConversationEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    DEFAULT_MODEL,
    DEFAULT_TOOLS_CONFIG_PATH,
    DEFAULT_PROMPT_PATH,
    DEFAULT_ALLOWED_DOMAINS,
    DEFAULT_ALLOWED_SERVICES,
)
from .mistral_agent import MistralConversationAgent

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,  # <-- 3e argument requis par HA
) -> None:
    """Set up the Mistral AI conversation platform."""
    api_key = entry.data.get("api_key")
    model = entry.options.get("model", DEFAULT_MODEL)
    tools_config_path = entry.options.get("tools_config_path", DEFAULT_TOOLS_CONFIG_PATH)
    prompt_path = entry.options.get("prompt_path", DEFAULT_PROMPT_PATH)
    allowed_domains = entry.options.get("allowed_domains", DEFAULT_ALLOWED_DOMAINS)
    allowed_services = entry.options.get("allowed_services", DEFAULT_ALLOWED_SERVICES)

    if not api_key:
        _LOGGER.error("API key for Mistral AI is not configured.")
        return

    agent = MistralConversationAgent(
        hass=hass,
        entry=entry,
        api_key=api_key,
        model=model,
        tools_config_path=tools_config_path,
        prompt_path=prompt_path,
        allowed_domains=allowed_domains,
        allowed_services=allowed_services,
    )

    # Utiliser le callback fourni par HA, pas de contournement manuel
    async_add_entities([agent])
