"""Conversation platform for Mistral AI."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.conversation import (
    ConversationEntity,
    ConversationEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import async_get_platform

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

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Mistral AI conversation platform."""
    api_key = entry.data.get("api_key")
    model = entry.options.get("model", DEFAULT_MODEL)
    tools_config_path = entry.options.get("tools_config_path", DEFAULT_TOOLS_CONFIG_PATH)
    prompt_path = entry.options.get("prompt_path", DEFAULT_PROMPT_PATH)
    allowed_domains = entry.options.get("allowed_domains", DEFAULT_ALLOWED_DOMAINS)
    allowed_services = entry.options.get("allowed_services", DEFAULT_ALLOWED_SERVICES)

    if not api_key:
        _LOGGER.error("API key for Mistral AI is not configured.")
        return False

    agent = MistralConversationAgent(
        hass=hass,
        entry_id=entry.entry_id,
        api_key=api_key,
        model=model,
        tools_config_path=tools_config_path,
        prompt_path=prompt_path,
        allowed_domains=allowed_domains,
        allowed_services=allowed_services,
    )

    # Ajouter l'agent comme entité de conversation
    platform = await async_get_platform(hass, "conversation")
    await platform.async_add_entities([agent])

    return True
