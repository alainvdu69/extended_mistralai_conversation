"""Custom Conversation Agent for Mistral AI (HA 2026.7.2)."""
from __future__ import annotations

import json
import logging
from typing import Any, Literal

import aiohttp
import yaml
from homeassistant.components import conversation
from homeassistant.components.conversation import (
    ConversationEntity,
    ConversationInput,
    ConversationResult,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.template import Template

_LOGGER = logging.getLogger(__name__)

class MistralConversationAgent(ConversationEntity, conversation.AbstractConversationAgent):
    """Conversation agent for Mistral AI with dynamic prompt and tools."""

    _attr_supported_features = ConversationEntityFeature.CONTROL

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the Mistral conversation agent."""
        super().__init__()
        self.hass = hass
        self.entry = entry  # <-- Stocke l'entrée de configuration
        self.api_key = entry.data.get("api_key")
        self.model = entry.options.get("model", "mistral-medium")
        self.tools_config_path = entry.options.get("tools_config_path", "config/mistral_tools.yaml")
        self.prompt_path = entry.options.get("prompt_path", "config/mistral_prompt.txt")
        self.allowed_domains = entry.options.get("allowed_domains", [])
        self.allowed_services = entry.options.get("allowed_services", {})
        self.session = aiohttp.ClientSession()
        self.tools = self._load_tools_config()
        self.prompt_template = self._load_prompt_template()
        self._attr_name = "Extended Mistral AI Conversation"
        self._attr_unique_id = f"mistral_agent_{entry.entry_id}"  # <-- Utilise entry.entry_id

    @property
    def name(self) -> str:
        """Retourne le nom de l'agent."""
        return self._attr_name

    @property
    def unique_id(self) -> str:
        """Retourne l'ID unique de l'agent."""
        return self._attr_unique_id

    @property
    def supported_languages(self) -> list[str]:
        """Retourne la liste des langues supportées par l'agent."""
        return ["fr"]

    def _load_tools_config(self) -> list[dict]:
        """Charge la configuration des tools depuis le fichier YAML."""
        try:
            with open(self.tools_config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config.get("tools", [])
        except Exception as e:
            _LOGGER.error(f"Erreur lors du chargement de {self.tools_config_path}: {e}")
            return []

    def _load_prompt_template(self) -> str:
        """Charge le template de prompt depuis le fichier texte."""
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            _LOGGER.error(f"Erreur lors du chargement de {self.prompt_path}: {e}")
            return ""

    def _get_exposed_entities(self) -> list[dict]:
        """Retourne la liste des entités exposées pour Assist."""
        exposed = []
        for entity in self.hass.states.async_all():
            if entity.attributes.get("assist", False):
                exposed.append({
                    "entity_id": entity.entity_id,
                    "name": entity.attributes.get("friendly_name", entity.entity_id),
                    "state": entity.state,
                    "aliases": entity.attributes.get("aliases", [])
                })
        return exposed

    def _get_areas(self) -> list[str]:
        """Retourne la liste des area_id."""
        return list(self.hass.helpers.area_registry.async_get_areas().keys())

    def _get_area_name(self, area_id: str) -> str:
        """Retourne le nom d'une area à partir de son ID."""
        area = self.hass.helpers.area_registry.async_get_area(area_id)
        return area.name if area else "Inconnu"

    def _convert_to_mistral_tool(self, tool_config: dict) -> dict:
        """Convertit un tool YAML en format Mistral API."""
        return {
            "type": "function",
            "function": {
                "name": tool_config["name"],
                "description": tool_config["description"],
                "parameters": tool_config["parameters"]
            }
        }

    async def async_added_to_hass(self) -> None:
        """Appelé quand l'entité est ajoutée à Home Assistant."""
        await super().async_added_to_hass()

    async def async_conversation_run(self, input: Any) -> Any:
        """Traite une requête de conversation."""
        from homeassistant.components.conversation import ConversationInput, ConversationResult
        user_input = input.context.get("user_input", {})
        rendered_prompt = await self._render_prompt(user_input)

        # Préparer les outils Mistral
        mistral_tools = [self._convert_to_mistral_tool(tool) for tool in self.tools]

        # Appeler Mistral API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": rendered_prompt},
                {"role": "user", "content": input.text}
            ],
            "tools": mistral_tools
        }

        try:
            async with self.session.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                response_data = await response.json()

                # Vérifier si Mistral a appelé une fonction
                if "tool_calls" in response_data["choices"][0]:
                    tool_call = response_data["choices"][0]["tool_calls"][0]
                    function_name = tool_call["function"]["name"]
                    arguments = json.loads(tool_call["function"]["arguments"])

                    if function_name == "execute_services":
                        # Vérifier les permissions pour execute_services
                        for service_call in arguments["list"]:
                            domain = service_call["domain"]
                            service = service_call["service"]

                            if domain not in self.allowed_domains:
                                return ConversationResult(
                                    response_type=intent.IntentResponseType.ERROR,
                                    speech=f"Désolé, le domaine {domain} n'est pas autorisé."
                                )

                            if service not in self.allowed_services.get(domain, []):
                                return ConversationResult(
                                    response_type=intent.IntentResponseType.ERROR,
                                    speech=f"Désolé, le service {service} pour le domaine {domain} n'est pas autorisé."
                                )

                            # Exécuter le service
                            service_data = service_call.get("service_data", {})
                            await self.hass.services.async_call(
                                domain,
                                service,
                                service_data
                            )

                        return ConversationResult(
                            response_type=intent.IntentResponseType.ACTION_DONE
                        )

                    else:
                        # Gérer les autres outils (assist_timer, add_event, etc.)
                        tool_config = next(
                            (t for t in self.tools if t["name"] == function_name),
                            None
                        )
                        if not tool_config:
                            return ConversationResult(
                                response_type=intent.IntentResponseType.ERROR,
                                speech=f"Tool {function_name} non trouvé."
                            )

                        rendered_data = self._render_template(
                            tool_config["function"]["sequence"][0]["data"],
                            arguments
                        )

                        if tool_config["function"]["type"] == "script":
                            await self.hass.services.async_call(
                                "script",
                                tool_config["function"]["sequence"][0]["action"].split(".")[1],
                                rendered_data
                            )
                        elif tool_config["function"]["type"] == "service":
                            await self.hass.services.async_call(
                                tool_config["function"]["domain"],
                                tool_config["function"]["service"],
                                rendered_data
                            )

                        return ConversationResult(
                            response_type=intent.IntentResponseType.ACTION_DONE
                        )

                # Réponse textuelle
                return ConversationResult(
                    response_type=intent.IntentResponseType.QUERY_ANSWER,
                    speech=response_data["choices"][0]["message"]["content"]
                )

        except Exception as e:
            _LOGGER.error(f"Erreur avec Mistral API: {e}")
            return ConversationResult(
                response_type=intent.IntentResponseType.ERROR,
                speech="Désolé, une erreur est survenue avec Mistral AI."
            )

    def _render_template(self, template_data: dict, arguments: dict) -> dict:
        """Rend un template Jinja2 avec les arguments fournis."""
        rendered = {}
        for key, value in template_data.items():
            if isinstance(value, str) and ("{{" in value or "{%" in value):
                # C'est un template Jinja2
                template = Template(value)
                rendered[key] = template.async_render(
                    variables={**arguments, **{"area_entities": self.hass.helpers.area_entities}}
                )
            else:
                rendered[key] = value
        return rendered

    async def _render_prompt(self, user_input: dict = None) -> str:
        """Rend le prompt complet avec Jinja2."""
        if not user_input:
            user_input = {}

        template_vars = {
            "now": self.hass.helpers.now,
            "exposed_entities": self._get_exposed_entities,
            "areas": self._get_areas,
            "area_name": self._get_area_name,
            "states": self.hass.states.get,
            "user_input": user_input,
        }

        template = Template(self.prompt_template)
        return template.async_render(variables=template_vars)
