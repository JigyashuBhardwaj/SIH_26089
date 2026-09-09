# features/worker/

Worker-flow feature logic used by the `(worker)` route group: booking
request accept/decline handling, accepted-request tracking, "mark
completed" flow, QR payment-collection initiation. Calls into
`../../shared/booking` for rules and `../../services` for API access — it
does not talk to the network directly.

Built in Phase 6 (Worker App). Empty for now.
