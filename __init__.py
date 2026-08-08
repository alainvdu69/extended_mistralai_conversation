"""Mistral AI Conversation Agent for Home Assistant 2026.7.2."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

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

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up via configuration.yaml (legacy)."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Mistral AI conversation agent from a config entry."""
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
        entry_id=entry.entry_id,  # <-- Passe entry.entry_id ici
        api_key=api_key,
        model=model,
        tools_config_path=tools_config_path,
        prompt_path=prompt_path,
        allowed_domains=allowed_domains,
        allowed_services=allowed_services,
    )

    await hass.helpers.entity_platform.async_get_platform("conversation").async_add_entities([agent])
    _LOGGER.info("Mistral AI Conversation Agent initialized successfully.")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True
    