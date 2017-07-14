web: newrelic-admin run-program uwsgi uwsgi.ini
worker: python manager.py rq worker --sentry-dsn $SENTRY_DSN
clock: python manager.py rq scheduler