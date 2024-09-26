# Frequenz Electricity Trading API Client Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

* Replace assert statements with proper exception handling
* Implement client instance reuse to avoid redundant TCP connections
* Move documentation and code examples to the documentation website
* Replace the local `PaginationParams` type with the `frequenz-client-common` one
* Remove dependency to `googleapis-common-protos`
* Replace `Energy` with `Power` for the `quantity` representation
* Add str function for `DeliveryPeriod` object
* Add integration tests for the API
* Add an equality function to the Order type

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
