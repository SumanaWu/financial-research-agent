# Modified on 2026-11-17 for local study distribution; display names and nonessential project links adjusted. See MODIFICATIONS.md.
"""marketbridge-data REST client package.

Provides :class:`MarketBridgeDataClient` for fetching aggregates from the
marketbridge-data market data proxy service.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from .client import MarketBridgeDataClient
from .mcp_client import DAILY_INTERVALS, MarketBridgeMCPClient, split_date_time

__all__ = [
    "DAILY_INTERVALS",
    "MarketBridgeDataClient",
    "MarketBridgeMCPClient",
    "close_marketbridge_data_client",
    "close_marketbridge_mcp_client",
    "get_marketbridge_data_client",
    "get_marketbridge_mcp_client",
    "split_date_time",
]

# -- Host-side singleton (service-token auth) --------------------------------

_client: Optional[MarketBridgeDataClient] = None
_lock = asyncio.Lock()


async def get_marketbridge_data_client() -> MarketBridgeDataClient:
    """Get or create a singleton :class:`MarketBridgeDataClient`."""
    global _client
    async with _lock:
        if _client is None:
            from src.config.settings import MARKETBRIDGE_DATA_URL

            service_token = __import__("os").getenv("INTERNAL_SERVICE_TOKEN", "")
            _client = MarketBridgeDataClient(base_url=MARKETBRIDGE_DATA_URL, service_token=service_token)
        return _client


async def close_marketbridge_data_client() -> None:
    """Close the singleton client (call on shutdown)."""
    global _client
    async with _lock:
        if _client is not None:
            await _client.close()
            _client = None


# -- Sandbox-side singleton (OAuth token-file auth) --------------------------

_mcp_client: Optional[MarketBridgeMCPClient] = None


def get_marketbridge_mcp_client() -> MarketBridgeMCPClient:
    """Get or create a singleton :class:`MarketBridgeMCPClient`."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MarketBridgeMCPClient()
    return _mcp_client


async def close_marketbridge_mcp_client() -> None:
    """Close the singleton MCP client (call on shutdown)."""
    global _mcp_client
    if _mcp_client is not None:
        await _mcp_client.close()
        _mcp_client = None
