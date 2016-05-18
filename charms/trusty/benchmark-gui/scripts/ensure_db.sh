#!/bin/bash

# Create cabs database if it doesn't exist

PSQL='sudo -u postgres psql'

cd /opt/collector-web

if ! $PSQL -l | grep cabs >/dev/null 2>&1 ; then
  $PSQL -c "CREATE DATABASE cabs WITH OWNER cabs;"
  .venv/bin/initialize_db production.ini
else
  juju-log "Database 'cabs' already exists, upgrading..."
  .venv/bin/alembic -c production.ini upgrade head || true
fi
