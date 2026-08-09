"""Fonctions rest et scrape : s'appuient sur les intégrations HA du même nom.

Nécessite "rest" et "scrape" dans les dependencies du manifest.json, sinon
homeassistant.components.rest / .scrape ne sont pas garanties chargées.
"""
from __future__ import annotations

import logging
from typing import Any

from bs4 import BeautifulSoup
from homeassistant.components import rest, scrape
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_METHOD,
    CONF_NAME,
    CONF_PAYLOAD,
    CONF_RESOURCE,
    CONF_TIMEOUT,
    CONF_VALUE_TEMPLATE,
    CONF_VERIFY_SSL,
)
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers.template import Template

from .base import Function

_LOGGER = logging.getLogger(__name__)


def _get_rest_data(hass: HomeAssistant, rest_config: dict[str, Any], arguments: dict[str, Any]) -> rest.data.RestData:
    """Construit un RestData à partir de la config, en rendant les templates éventuels."""
    rest_config = dict(rest_config)
    rest_config.setdefault(CONF_METHOD, rest.const.DEFAULT_METHOD)
    rest_config.setdefault(CONF_VERIFY_SSL, rest.const.DEFAULT_VERIFY_SSL)
    rest_config.setdefault(CONF_TIMEOUT, rest.data.DEFAULT_TIMEOUT)
    rest_config.setdefault(rest.const.CONF_ENCODING, rest.const.DEFAULT_ENCODING)

    resource_template = rest_config.get("resource_template")
    if resource_template is not None:
        rest_config.pop("resource_template")
        rest_config[CONF_RESOURCE] = Template(resource_template, hass).async_render(arguments, parse_result=False)

    payload_template = rest_config.get("payload_template")
    if payload_template is not None:
        rest_config.pop("payload_template")
        rest_config[CONF_PAYLOAD] = Template(payload_template, hass).async_render(arguments, parse_result=False)

    return rest.create_rest_data_from_config(hass, rest_config)


class RestFunction(Function):
    async def execute(
        self,
        hass: HomeAssistant,
        function_config: dict[str, Any],
        arguments: dict[str, Any],
        context: Context | None,
        exposed_entities: list[dict[str, Any]],
    ) -> Any:
        rest_data = _get_rest_data(hass, function_config, arguments)
        await rest_data.async_update()
        value = rest_data.data_without_xml()

        value_template = function_config.get(CONF_VALUE_TEMPLATE)
        if value is not None and value_template is not None:
            value = Template(value_template, hass).async_render_with_possible_json_value(value, None, arguments)
        return value


class ScrapeFunction(Function):
    async def execute(
        self,
        hass: HomeAssistant,
        function_config: dict[str, Any],
        arguments: dict[str, Any],
        context: Context | None,
        exposed_entities: list[dict[str, Any]],
    ) -> Any:
        rest_data = _get_rest_data(hass, function_config, arguments)
        coordinator = scrape.coordinator.ScrapeCoordinator(
            hass, None, rest_data, function_config, scrape.const.DEFAULT_SCAN_INTERVAL,
        )
        await coordinator.async_refresh()

        new_arguments = dict(arguments)
        for sensor_config in function_config["sensor"]:
            value = self._extract_value(coordinator.data, sensor_config)
            value_template = sensor_config.get(CONF_VALUE_TEMPLATE)
            if value_template is not None:
                value = Template(value_template, hass).async_render_with_possible_json_value(value, None, arguments)
            new_arguments["value"] = value
            name = sensor_config.get(CONF_NAME)
            if name:
                new_arguments[Template(name, hass).async_render()] = value

        result = new_arguments["value"]
        value_template = function_config.get(CONF_VALUE_TEMPLATE)
        if value_template is not None:
            result = Template(value_template, hass).async_render_with_possible_json_value(result, None, new_arguments)
        return result

    def _extract_value(self, data: BeautifulSoup, sensor_config: dict[str, Any]) -> Any:
        select = sensor_config[scrape.const.CONF_SELECT]
        index = sensor_config.get(scrape.const.CONF_INDEX, 0)
        attr = sensor_config.get(CONF_ATTRIBUTE)
        try:
            if attr is not None:
                return data.select(select)[index][attr]
            tag = data.select(select)[index]
            return tag.string if tag.name in ("style", "script", "template") else tag.text
        except IndexError:
            _LOGGER.warning("Index '%s' introuvable pour le sélecteur '%s'", index, select)
        except KeyError:
            _LOGGER.warning("Attribut '%s' introuvable pour le sélecteur '%s'", attr, select)
        return None
