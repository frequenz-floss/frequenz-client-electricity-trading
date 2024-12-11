# Frequenz Electricity Trading API Client Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

* Extra validation check to ensure the quantity is strictly positive.
* Extra validation check to ensure the quantity and price are within the allowed bounds.
* Add more edge cases to the integration tests.
* Add idiomatic string representations for `Power` and `Price` classes.
* Add support for timeouts in the gRPC function calls
* Export Client constants for external use
* Fetch subsequent paginated data for `list_*` methods

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
