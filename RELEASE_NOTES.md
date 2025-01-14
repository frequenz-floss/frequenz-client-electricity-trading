# Frequenz Electricity Trading API Client Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

* Add trading-cli tool to interact with the trading API. Supports the following commands:
  * `list-day-ahead`: Listing day-ahead prices from the entsoe API.
  * `list-trades`: Listing and streaming public trades for specified delivery periods. If no delivery start is given, starts streaming all new public trades.
  * `list-orders`: Listing and streaming orders for specified delivery periods and gridpool IDs. If no delivery start is given, starts streaming all new orders for this gridpool ID.


<!-- Here goes the main new features and examples or instructions on how to use them -->

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
