# License: MIT
# Copyright © 2025 Frequenz Energy-as-a-Service GmbH

"""Functions for CLI tool to interact with the trading API."""

from datetime import datetime

import pandas as pd
from entsoe import EntsoePandasClient


def list_day_ahead_prices(
    entsoe_key: str,
    start: datetime,
    end: datetime,
    country_code: str,
) -> None:
    """
    List day-ahead prices for a given country code.

    Args:
        entsoe_key: The API key for the Entsoe API
        start: The start date of the query
        end: The end date of the query
        country_code: The country code for which to query the prices
    """
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)

    client = EntsoePandasClient(api_key=entsoe_key)
    da_prices = client.query_day_ahead_prices(country_code, start=start_ts, end=end_ts)

    da_prices.name = "price"
    da_prices.index.name = "timestamp"

    print(da_prices.to_csv())
