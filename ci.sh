#!/bin/bash
export JUJU_REPOSITORY="$(pwd)/charms"    # Use the repository jenkins gave us
export RESULTS_DIR = "/var/www/html"      # HTML test results will be put in $RESULTS_DIR/<bundle-name>

# TODO: only build affected bundles
echo "previous succesfull commit: $GIT_PREVIOUS_SUCCESSFUL_COMMIT"

# Download files that are too big for the git repository
tengu downloadbigfiles

# Test bundles (this script will fail if tests fail)
./cihelpers.py test bundles/storm bundles/spark $RESULTS_DIR
