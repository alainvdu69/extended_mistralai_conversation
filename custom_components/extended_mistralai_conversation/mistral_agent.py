"""Custom Conversation Agent for Mistral AI (HA 2026.7.2)."""
from __future__ import annotations

import json
import logging
from typing import Literal

from homeassistant.components import conversation
from homeassistant.components.conversation import (
    ConversationEntity,
    ConversationEntityFeature,
    ConversationInput,
    ConversationResult,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import intent
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

class MistralConversationAgent(ConversationEntity, conversation.AbstractConversationAgent):
    """Conversation agent for Mistral AI with dynamic prompt and tools."""

    _attr_supported_features = ConversationEntityFeature.CONTROL
    MAX_FUNCTION_CALLS = 5  # <-- garde-fou anti-boucle infinie (cf. jekalmin "Maximum Function Calls Per Conversation")

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api_key: str,
        model: str,
        tools: list[dict],
        prompt_template: str,
        allowed_domains: list[str],
        allowed_services: dict,
    ):
        """Initialize the Mistral conversation agent.

        tools et prompt_template sont déjà chargés depuis le disque par
        async_setup_entry (conversation.py) via l'executor, pour ne jamais
        faire d'I/O bloquant ici : __init__ ne peut pas être async, donc
        aucun hass.async_add_executor_job n'est possible à cet endroit.
        """
        super().__init__()
        self.hass = hass
        self.entry = entry  # <-- Stocke l'entrée de configuration
        self.api_key = api_key
        self.model = model
        self.allowed_domains = allowed_domains
        self.allowed_services = allowed_services
        self.session = async_get_clientsession(hass)  # <-- réutilise la session HA, pas de session orpheline non fermée
        self.tools = tools
        self.prompt_template = prompt_template
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
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Retourne la liste des langues supportées par l'agent."""
        return ["fr"]

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
        return list(ar.async_get(self.hass).areas)

    def _get_area_name(self, area_id: str) -> str:
        """Retourne le nom d'une area à partir de son ID."""
        area = ar.async_get(self.hass).async_get_area(area_id)
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
        conversation.async_set_agent(self.hass, self.entry, self)  # <-- rend l'agent sélectionnable dans Assist

    async def async_will_remove_from_hass(self) -> None:
        """Appelé quand l'entité est retirée."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        """Point d'entrée appelé par Home Assistant."""
        intent_response = intent.IntentResponse(language=user_input.language)
        try:
            speech = await self._async_conversation_run(user_input)
            intent_response.async_set_speech(speech)
        except Exception as e:
            _LOGGER.error(f"Erreur avec Mistral API: {e}")
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                "Désolé, une erreur est survenue avec Mistral AI.",
            )
        return ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id,
        )

    async def _async_conversation_run(self, user_input: ConversationInput) -> str:
        """Traite une requête de conversation et renvoie le texte final formulé par Mistral."""
        rendered_prompt = await self._render_prompt(user_input)
        mistral_tools = [self._convert_to_mistral_tool(tool) for tool in self.tools]

        messages = [
            {"role": "system", "content": rendered_prompt},
            {"role": "user", "content": user_input.text},
        ]

        return await self._query_mistral(messages, mistral_tools, n_calls=0)

    async def _query_mistral(
        self, messages: list[dict], mistral_tools: list[dict], n_calls: int
    ) -> str:
        """Appelle Mistral, exécute les tool_calls demandés, et relance jusqu'à obtenir une réponse texte."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": mistral_tools
        }

        async with self.session.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload
        ) as response:
            response_data = await response.json()

        message = response_data["choices"][0]["message"]  # <-- tool_calls est niché ici, pas sur "choices"[0] directement
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            # Réponse texte finale : c'est Mistral qui formule, selon les instructions du prompt
            return message.get("content", "")

        if n_calls >= self.MAX_FUNCTION_CALLS:
            _LOGGER.warning("Nombre maximum d'appels de fonction atteint (%s)", self.MAX_FUNCTION_CALLS)
            return "Désolé, je n'arrive pas à terminer cette action."

        # L'historique doit inclure le message assistant contenant les tool_calls avant les réponses "tool"
        messages.append(message)

        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])
            result_text = await self._execute_function(function_name, arguments)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": function_name,
                "content": result_text,
            })

        # On relance Mistral avec les résultats, pour qu'il formule la réponse finale
        return await self._query_mistral(messages, mistral_tools, n_calls + 1)

    async def _execute_function(self, function_name: str, arguments: dict) -> str:
        """Exécute une fonction demandée par Mistral et renvoie un message texte (succès ou erreur)."""
        if function_name == "execute_services":
            # Vérifier les permissions pour execute_services
            for service_call in arguments["list"]:
                domain = service_call["domain"]
                service = service_call["service"]

                if domain not in self.allowed_domains:
                    return f"Le domaine {domain} n'est pas autorisé."

                if service not in self.allowed_services.get(domain, []):
                    return f"Le service {service} pour le domaine {domain} n'est pas autorisé."

                # Exécuter le service
                service_data = service_call.get("service_data", {})
                await self.hass.services.async_call(
                    domain,
                    service,
                    service_data
                )

            return "Action réalisée avec succès."

        # Gérer les autres outils (assist_timer, add_event, etc.)
        tool_config = next(
            (t for t in self.tools if t["name"] == function_name),
            None
        )
        if not tool_config:
            return f"Tool {function_name} non trouvé."

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

        return "Action réalisée avec succès."

    def _render_template(self, template_data: dict, arguments: dict) -> dict:
        """Rend un template Jinja2 avec les arguments fournis."""
        rendered = {}
        for key, value in template_data.items():
            if isinstance(value, str) and ("{{" in value or "{%" in value):
                # C'est un template Jinja2 — area_entities() est déjà disponible nativement
                # dans l'environnement Jinja de HA, pas besoin de l'injecter manuellement
                template = Template(value, self.hass)
                rendered[key] = template.async_render(variables=arguments)
            else:
                rendered[key] = value
        return rendered

    async def _render_prompt(self, user_input: ConversationInput | None = None) -> str:
        """Rend le prompt complet avec Jinja2."""
        template_vars = {
            "now": dt_util.now,
            "exposed_entities": self._get_exposed_entities,
            "areas": self._get_areas,
            "area_name": self._get_area_name,
            "states": self.hass.states.get,
            "user_input": user_input,
        }

        template = Template(self.prompt_template, self.hass)
        return template.async_render(variables=template_vars)
