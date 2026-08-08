"""Conversation platform for Mistral AI."""
from __future__ import annotations

import logging

import yaml
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


def _load_tools_config(path: str) -> list[dict]:
    """Charge la configuration des tools depuis le fichier YAML (fonction synchrone, à exécuter via l'executor)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config.get("tools", [])
    except Exception as e:
        _LOGGER.error(f"Erreur lors du chargement de {path}: {e}")
        return []


def _load_prompt_template(path: str) -> str:
    """Charge et assemble le prompt (YAML static_prompt + dynamic_prompt) depuis le disque (fonction synchrone, à exécuter via l'executor)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        static_prompt = config.get("static_prompt", "")
        dynamic_prompt = config.get("dynamic_prompt", "")
        return f"{static_prompt}\n{dynamic_prompt}"
    except Exception as e:
        _LOGGER.error(f"Erreur lors du chargement de {path}: {e}")
        return ""


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

    # Lecture disque effectuée ici, hors du constructeur de l'entité,
    # via l'executor pour ne pas bloquer la boucle asyncio (cf. avertissement HA)
    tools = await hass.async_add_executor_job(_load_tools_config, tools_config_path)
    prompt_template = await hass.async_add_executor_job(_load_prompt_template, prompt_path)

    agent = MistralConversationAgent(
        hass=hass,
        entry=entry,
        api_key=api_key,
        model=model,
        tools=tools,
        prompt_template=prompt_template,
        allowed_domains=allowed_domains,
        allowed_services=allowed_services,
    )

    # Utiliser le callback fourni par HA, pas de contournement manuel
    async_add_entities([agent])
