"""Sensors for Oracle integration."""
from __future__ import annotations


from datetime import timedelta, date
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_HOST
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensors for Oracle."""
    domain_data = hass.data[DOMAIN].setdefault(entry.entry_id, {})
    session = hass.helpers.aiohttp_client.async_get_clientsession()
    from .adguard_client import AdGuardApi

    client = AdGuardApi(session, entry.data.get(CONF_HOST), entry.data.get("username"), entry.data.get("password"))

    async def async_update():
        try:
            clients = await client.async_get_clients()
            # Attach recent queries per client if possible
            for c in clients:
                ip = c.get("ip") or c.get("client_ip") or c.get("address")
                if ip:
                    queries = await client.async_get_queries(ip)
                    c["queries"] = queries or []
            return clients
        except Exception as err:
            raise UpdateFailed(err)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="oracle",
        update_method=async_update,
        update_interval=timedelta(seconds=entry.options.get("scan_interval", entry.data.get("scan_interval", 60))),
    )

    await coordinator.async_refresh()

    # Persist coordinator and client for other platforms
    domain_data["coordinator"] = coordinator
    domain_data["client"] = client

    entities: list[SensorEntity] = []
    for c in coordinator.data or []:
        name = c.get("name") or c.get("hostname") or c.get("ip") or c.get("client_ip")
        entities.append(OracleDeviceSensor(coordinator, entry, name, c))

    async_add_entities(entities)


class OracleDeviceSensor(SensorEntity):
    """Sensor representing query metrics for a client device."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry, name: str, client: dict[str, Any]):
        self.coordinator = coordinator
        self._entry = entry
        self._attr_name = f"Oracle {name} Queries Today"
        self._client = client
        self._attr_extra_state_attributes = {}

    @property
    def unique_id(self):
        return (self._client.get("id") or self._client.get("ip") or self._client.get("client_ip"))

    @property
    def state(self):
        # Return today's query count
        queries = self._client.get("queries", [])
        today = date.today().isoformat()
        # Try to filter queries that have timestamp today if possible
        count = 0
        for q in queries:
            ts = q.get("ts") or q.get("time") or q.get("timestamp")
            if not ts:
                count += 1
            else:
                try:
                    # if ts is numeric epoch seconds
                    if isinstance(ts, (int, float)):
                        qdate = date.fromtimestamp(int(ts))
                    else:
                        # naive parse YYYY-MM-DD
                        qdate = date.fromisoformat(str(ts).split("T")[0])
                    if qdate.isoformat() == today:
                        count += 1
                except Exception:
                    count += 1

        # Update history in storage
        store = self.coordinator.hass.data[DOMAIN].get(self._entry.entry_id, {}).get("store")
        if store:
            data = self.coordinator.hass.data[DOMAIN].get(self._entry.entry_id, {}).get("data", {})
            hist = data.setdefault("history", {})
            key = self.unique_id or "unknown"
            hist.setdefault(key, {})[today] = count
            # keep last 30 days
            # save asynchronously
            try:
                self.coordinator.hass.async_create_task(store.async_save(data))
            except Exception:
                _LOGGER.debug("Failed saving history")

        # compute average per day from history
        avg = None
        try:
            hist_for = self.coordinator.hass.data[DOMAIN].get(self._entry.entry_id, {}).get("data", {}).get("history", {}).get(self.unique_id, {})
            if hist_for:
                vals = list(hist_for.values())
                avg = sum(vals) / len(vals)
        except Exception:
            avg = None

        self._attr_extra_state_attributes = {"avg_per_day": avg}

        return count

    async def async_update(self):
        await self.coordinator.async_request_refresh()
