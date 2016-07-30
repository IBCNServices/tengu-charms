#!/bin/bash
set -e

export JUJU_REPOSITORY="$(pwd)/charms"    # Use the repository jenkins gave us
export RESULTS_DIR="/var/www/html"      # HTML test results will be put in $RESULTS_DIR/<bundle-name>

# TODO: only build affected bundles
echo "previous succesfull commit: $GIT_PREVIOUS_SUCCESSFUL_COMMIT"

#workaround for https://bugs.launchpad.net/juju/+bug/1592822
rm -f charms/trusty/rest2jfed/files/jfedS4/jfed_cli.tar.gz.source
rm -f charms/trusty/rest2jfed/files/jdk-8u77-linux-x64.tar.gz.source
# Download files that are too big for the git repository
tengu downloadbigfiles


# Test bundles (this script will fail if tests fail)
./cihelpers.py test bundles/streaming/bundle.yaml bundles/microbatch/bundle.yaml $RESULTS_DIR
