"""WS-03 Celery task layer (ADR-008).

Tasks accept identifiers/small metadata only, load input from shared
storage, and persist durable outcomes through the application service
layer under app/services — never by writing models directly and never by
carrying file binaries in the task payload.

Task submodules are imported (and thereby registered with celery_app) from
app/celery_app.py, not here, to avoid a circular import.
"""
