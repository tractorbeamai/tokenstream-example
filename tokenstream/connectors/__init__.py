"""Source connectors, one module per source.

Almost every feed is a custom ``@tb.Connector`` that emits its rows inline; Stripe is
the lone ``tb.ManagedConnector``. So the example runs end-to-end without credentials,
each ``@tb.output`` generates synthetic sample data on its real-world cadence. The
modules are discovered by the workspace walk, so this package intentionally does not
eagerly import them (eager imports would double-fire the decorators).
"""
