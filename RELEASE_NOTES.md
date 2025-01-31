# Frequenz Electricity Trading API Client Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

* Add trading-cli tool to interact with the trading API. Supports the following commands:
  * `list-day-ahead`: Listing day-ahead prices from the entsoe API.
  * `receive-trades`: Listing and streaming public trades for specified delivery periods. If no delivery start is given, starts streaming all new public trades.
  * `receive-orders`: Listing and streaming orders for specified delivery periods and gridpool IDs. If no delivery start is given, starts streaming all new orders for this gridpool ID.
  * `create-order`: Creating a limit order for a given price (in EUR/MWh) and quantity (in MW, sign determines market side).
  * `cancel-order`: Cancel individual orders for a gridpool.
  * `cancel-all-orders`: Cancels all orders of a gridpool.


<!-- Here goes the main new features and examples or instructions on how to use them -->

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
