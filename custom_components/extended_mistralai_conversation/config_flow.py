"""Config flow for Mistral AI Conversation integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import yaml
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .const import (
    DOMAIN,
    DEFAULT_MODEL,
    DEFAULT_TOOLS_CONFIG_PATH,
    DEFAULT_PROMPT_PATH,
    DEFAULT_ALLOWED_DOMAINS,
    DEFAULT_ALLOWED_SERVICES,
)

_LOGGER = logging.getLogger(__name__)

class MistralAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mistral AI Conversation."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required("api_key"): str,
                        vol.Optional("model", default=DEFAULT_MODEL): str,
                    }
                ),
            )

        return self.async_create_entry(
            title="Extended Mistral AI Conversation",
            data={"api_key": user_input["api_key"]},
            options={
                "model": user_input.get("model", DEFAULT_MODEL),
                "tools_config_path": DEFAULT_TOOLS_CONFIG_PATH,
                "prompt_path": DEFAULT_PROMPT_PATH,
                "allowed_domains": DEFAULT_ALLOWED_DOMAINS,
                "allowed_services": DEFAULT_ALLOWED_SERVICES,
            }
        )

    async def async_step_import(self, import_config: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_config)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MistralOptionsFlowHandler:
        """Create the options flow, permettant de modifier les valeurs par défaut après création."""
        return MistralOptionsFlowHandler()


class MistralOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Extended Mistral AI Conversation.

    Depuis HA récent, self.config_entry est une propriété héritée de OptionsFlow,
    accessible uniquement APRÈS __init__ (jamais dans __init__ lui-même) — donc
    pas de __init__ à définir ici, contrairement aux anciennes versions de HA.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        current = self.config_entry.options
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                allowed_domains = [
                    d.strip() for d in user_input["allowed_domains"].split(",") if d.strip()
                ]
                allowed_services = yaml.safe_load(user_input["allowed_services"]) or {}
                if not isinstance(allowed_services, dict):
                    raise ValueError("allowed_services doit être un mapping YAML (domaine -> liste de services)")
            except Exception as e:
                _LOGGER.error(f"Erreur de validation des options: {e}")
                errors["base"] = "invalid_yaml"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        "model": user_input["model"],
                        "tools_config_path": user_input["tools_config_path"],
                        "prompt_path": user_input["prompt_path"],
                        "allowed_domains": allowed_domains,
                        "allowed_services": allowed_services,
                    },
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional("model", default=current.get("model", DEFAULT_MODEL)): str,
                    vol.Optional(
                        "tools_config_path",
                        default=current.get("tools_config_path", DEFAULT_TOOLS_CONFIG_PATH),
                    ): str,
                    vol.Optional(
                        "prompt_path",
                        default=current.get("prompt_path", DEFAULT_PROMPT_PATH),
                    ): str,
                    vol.Optional(
                        "allowed_domains",
                        default=", ".join(current.get("allowed_domains", DEFAULT_ALLOWED_DOMAINS)),
                    ): str,
                    vol.Optional(
                        "allowed_services",
                        default=yaml.dump(
                            current.get("allowed_services", DEFAULT_ALLOWED_SERVICES),
                            allow_unicode=True,
                            sort_keys=False,
                        ),
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT, multiline=True)),
                }
            ),
            errors=errors,
        )
