#!/bin/bash

# Create cabs database user if it doesn't exist

PSQL='sudo -u postgres psql'

if ! $PSQL -c '\dg' | grep cabs >/dev/null 2>&1 ; then
  $PSQL -c "CREATE USER cabs WITH UNENCRYPTED PASSWORD 'cabs';"
else
  juju-log "Database user 'cabs' already exists, skipping creation."
fi
