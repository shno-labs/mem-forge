# Project source sync activity from existing execution records

Local collection jobs and server processing runs keep their independent durable lifecycles because they have different owners, leases, retries, and storage transactions. The Sources UI consumes one Source Sync Activity read model projected from those records, rather than introducing a cross-store master operation or extending the server processing run to own device collection.

This keeps execution recovery local to each existing state machine while giving every source type one refresh-safe progress contract and presenter. Server processing persists its latest Progress Snapshot on its run; local collection exposes the snapshot already persisted with its job. The projection selects the relevant activity and never treats progress-delivery failure as source-sync failure.
