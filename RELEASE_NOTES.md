# Frequenz Electricity Trading API Client Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

* Rename CLI trade and order functions for clarity
    * Rename `receive_trades` to `receive_public_trades`
    * Rename `receive_orders` to `receive_gridpool_orders`

- The `stream_*` methods in the client have been renamed to `*_stream`.  They no longer return `Receiver` instances, but rather `GrpcStreamBroadcaster` instances.  They expose a `new_receiver()` method which can be used to get a new receiver.  They also expose a `stop()` method which can be used to stop the background streaming task when the stream is no longer needed.

## New Features

* Print tags and filled (instead of open) quantity for gridpool orders in CLI tool.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
