# Modified on 2026-11-17 for local study distribution; display names and nonessential project links adjusted. See MODIFICATIONS.md.
"""Backward-compatible re-export — use ``data_source`` instead."""

from .data_source import MarketBridgeDataSource as MarketBridgeDataPriceProvider  # noqa: F401

__all__ = ["MarketBridgeDataPriceProvider"]
