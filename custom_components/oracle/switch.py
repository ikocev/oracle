"""Switch platform to mark devices as controlled."""
from __future__ import annotations

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_HOST

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up switches representing whether a device is controlled."""
    domain_data = hass.data[DOMAIN].setdefault(entry.entry_id, {})
    coordinator = domain_data.get("coordinator")
    data = domain_data.get("data", {})

    controlled = set(data.get("controlled_devices", []))

    entities: list[SwitchEntity] = []
    # if coordinator is available, create one switch per client
    if coordinator and coordinator.data:
        for c in coordinator.data:
            ip = c.get("ip") or c.get("client_ip") or c.get("address")
            name = c.get("name") or c.get("hostname") or ip
            entities.append(OracleControlledSwitch(entry.entry_id, ip, name, hass))

        async_add_entities(entities)
    else:
        # coordinator not ready yet — schedule a retry to create entities
        async def _try_late_setup(_now):
            domain_data = hass.data[DOMAIN].get(entry.entry_id, {})
            coord = domain_data.get("coordinator")
            if not coord or not coord.data:
                return
            late_entities: list[SwitchEntity] = []
            for c in coord.data:
                ip = c.get("ip") or c.get("client_ip") or c.get("address")
                name = c.get("name") or c.get("hostname") or ip
                late_entities.append(OracleControlledSwitch(entry.entry_id, ip, name, hass))
            if late_entities:
                async_add_entities(late_entities)

        from homeassistant.helpers.event import async_call_later

        async_call_later(hass, 5, _try_late_setup)


class OracleControlledSwitch(SwitchEntity):
    """Represents whether a client is controlled by Oracle."""

    def __init__(self, entry_id: str, client_ip: str, name: str, hass: Any):
        self._entry_id = entry_id
        self._client_ip = client_ip or "unknown"
        self._hass = hass
        self._attr_name = f"Oracle Controlled {name}"

    @property
    def unique_id(self) -> str:
        return f"{self._entry_id}_{self._client_ip}"

    @property
    def is_on(self) -> bool:
        data = self._hass.data[DOMAIN].get(self._entry_id, {}).get("data", {})
        controlled = set(data.get("controlled_devices") or [])
        return self._client_ip in controlled

    async def async_turn_on(self, **kwargs):
        domain = self._hass.data[DOMAIN].get(self._entry_id, {})
        store = domain.get("store")
        data = domain.setdefault("data", {})
        controlled = set(data.get("controlled_devices") or [])
        controlled.add(self._client_ip)
        data["controlled_devices"] = list(controlled)
        if store:
            await store.async_save(data)
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        domain = self._hass.data[DOMAIN].get(self._entry_id, {})
        store = domain.get("store")
        data = domain.setdefault("data", {})
        controlled = set(data.get("controlled_devices") or [])
        controlled.discard(self._client_ip)
        data["controlled_devices"] = list(controlled)
        if store:
            await store.async_save(data)
        self.async_schedule_update_ha_state()
