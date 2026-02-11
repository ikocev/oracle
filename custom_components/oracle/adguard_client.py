"""Minimal AdGuard Home API client wrapper."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class AdGuardApi:
    """Simple AdGuard Home API client using Basic Auth."""

    def __init__(self, session: aiohttp.ClientSession, host: str, username: str = "", password: str = ""):
        self._session = session
        host = host.rstrip("/")
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"
        self._host = host
        self._auth = aiohttp.BasicAuth(username, password) if username or password else None

    def _url(self, path: str) -> str:
        return f"{self._host}{path}"

    async def async_get_clients(self) -> list[dict[str, Any]]:
        """Return list of clients known to AdGuard Home."""
        url = self._url("/control/clients")
        async with self._session.get(url, auth=self._auth, raise_for_status=True) as resp:
            data = await resp.json()
            if isinstance(data, list):
                return data
            # v0.107+ returns dict with 'clients' and 'auto_clients'
            clients = data.get("clients", [])
            auto_clients = data.get("auto_clients", [])
            
            raw_list = clients + auto_clients
            final_list = []
            for item in raw_list:
                if isinstance(item, dict):
                    final_list.append(item)
                elif isinstance(item, str):
                    # handle if API returns list of IPs/IDs as strings
                    final_list.append({"ip": item, "name": item, "ids": [item]})
            
            return final_list

    async def async_get_queries(self, client_id: str | None = None) -> list[dict[str, Any]]:
        """Return recent DNS queries. If client_id given, filter by it if API supports it."""
        url = self._url("/control/querylog")
        params = {}
        if client_id:
            params["search"] = client_id
        
        try:
            async with self._session.get(url, params=params, auth=self._auth) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # API returns dict with "data" list
                    return data.get("data", [])
        except Exception:
            pass
        return []

    async def async_block_domain_for_client(self, client_ip: str, domain: str) -> bool:
        """Block a domain for a specific client using custom filtering rules."""
        # AdGuard Home v0.107 custom rules API:
        # 1. GET /control/filtering/status to get current 'user_rules'
        # 2. Append new rule
        # 3. POST /control/filtering/set_rules with updated list
        
        # Rule syntax for specific client: ||example.com^$client='192.168.1.50'
        # Note: client identifier can be IP or ClientID
        rule = f"||{domain}^$client='{client_ip}'"
        
        try:
            # 1. Get current rules
            status_url = self._url("/control/filtering/status")
            async with self._session.get(status_url, auth=self._auth) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                current_rules = data.get("user_rules", [])

            if rule in current_rules:
                return True

            # 2. Add rule
            current_rules.append(rule)

            # 3. Set rules
            set_url = self._url("/control/filtering/set_rules")
            # The API expects just the list of strings in "rules"
            payload = {"rules": current_rules}
            async with self._session.post(set_url, json=payload, auth=self._auth) as resp:
                return resp.status == 200
        except Exception:
            return False
