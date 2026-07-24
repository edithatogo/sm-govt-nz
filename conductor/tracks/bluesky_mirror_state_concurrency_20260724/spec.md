# Specification

Partition mutable runtime state by mirror ID and keep audit events append-only. Account jobs must update only their own state file. Aggregate reports are regenerated from partitioned state. Conflict-safe commits must preserve unrelated account updates and support migration from the monolithic state file.
