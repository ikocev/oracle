"""The Oracle integration."""
from __future__ import annotations

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import storage

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Support both sensor and switch platforms
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

STORE_VERSION = 1


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Oracle from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    domain_data = hass.data[DOMAIN].setdefault(entry.entry_id, {})

    # create a storage helper to persist controlled devices and history
    store_key = f"{DOMAIN}_{entry.entry_id}"
    store = storage.Store(hass, STORE_VERSION, store_key)
    data = await store.async_load()
    if not data:
        data = {"controlled_devices": [], "history": {}}
        await store.async_save(data)

    domain_data["store"] = store
    domain_data["data"] = data

    # Save a short helper for poll interval
    domain_data["scan_interval"] = entry.options.get("scan_interval", entry.data.get("scan_interval", 60))

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration services."""

    async def mark_controlled(call):
        entry_id = call.data.get("entry_id")
        client_ip = call.data.get("client_ip")
        # find the entry
        if not entry_id:
            # use first entry
            entries = hass.config_entries.async_entries(DOMAIN)
            if not entries:
                return
            entry_id = entries[0].entry_id

        domain = hass.data[DOMAIN].get(entry_id, {})
        store = domain.get("store")
        data = domain.setdefault("data", {})
        controlled = set(data.get("controlled_devices", []))
        controlled.add(client_ip)
        data["controlled_devices"] = list(controlled)
        if store:
            await store.async_save(data)

    async def unmark_controlled(call):
        entry_id = call.data.get("entry_id")
        client_ip = call.data.get("client_ip")
        if not entry_id:
            entries = hass.config_entries.async_entries(DOMAIN)
            if not entries:
                return
            entry_id = entries[0].entry_id

        domain = hass.data[DOMAIN].get(entry_id, {})
        store = domain.get("store")
        data = domain.setdefault("data", {})
        controlled = set(data.get("controlled_devices", []))
        controlled.discard(client_ip)
        data["controlled_devices"] = list(controlled)
        if store:
            await store.async_save(data)

    async def refresh_now(call):
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            domain = hass.data[DOMAIN].get(entry.entry_id, {})
            coord = domain.get("coordinator")
            if coord:
                await coord.async_refresh()

    hass.services.async_register(DOMAIN, "mark_controlled", mark_controlled)
    hass.services.async_register(DOMAIN, "unmark_controlled", unmark_controlled)
    hass.services.async_register(DOMAIN, "refresh_now", refresh_now)

    return True
