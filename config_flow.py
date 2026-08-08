"""Config flow for Mistral AI Conversation integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

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
                        vol.Optional("tools_config_path", default=DEFAULT_TOOLS_CONFIG_PATH): str,
                        vol.Optional("prompt_path", default=DEFAULT_PROMPT_PATH): str,
                        vol.Optional("allowed_domains", default=DEFAULT_ALLOWED_DOMAINS): list,
                        vol.Optional("allowed_services", default=DEFAULT_ALLOWED_SERVICES): dict,
                    }
                ),
            )

        return self.async_create_entry(
            title="Extended Mistral AI Conversation",
            data={"api_key": user_input["api_key"]},
            options={
                "model": user_input.get("model", DEFAULT_MODEL),
                "tools_config_path": user_input.get("tools_config_path", DEFAULT_TOOLS_CONFIG_PATH),
                "prompt_path": user_input.get("prompt_path", DEFAULT_PROMPT_PATH),
                "allowed_domains": user_input.get("allowed_domains", DEFAULT_ALLOWED_DOMAINS),
                "allowed_services": user_input.get("allowed_services", DEFAULT_ALLOWED_SERVICES),
            }
        )

    async def async_step_import(self, import_config: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_config)
        