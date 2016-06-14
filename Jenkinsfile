/*
  Copyright (C) 2016  Ghent University

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.


  This file is the Jenkins Pipeline script for the CI pipeline for the Tengu charms.
*/
node {
  echo 'Pipeline Start'
  stage 'Checkout'
  git url: 'https://github.com/IBCNServices/tengu-charms/'
  env.JUJU_REPOSITORY = pwd() + '/charms'
  def resultsDir = "/var/www/html"

  stage 'Download Bigfiles'
  sh 'tengu downloadbigfiles'

  try {
    /*
      run tests according to testplan in repo root.
    */
    stage 'Test'
    sh "cwr --no-destroy tenguci testplan.yaml --no-destroy -l DEBUG -o ${resultsDir}"
  } finally {
    /*
      publish test results even when tests failed. apache2 needs to be
      installed for this to work. Default apache2 config is ok.
    */
    stage 'Publish Test results'
    sh "cp `ls -dt ${resultsDir}/* | grep result.html | head -1` ${resultsDir}/index.html"

    /*
      this is here so the "Publish Test results" stage doesn't appear 'crashed'
      when the "Test" stage crashed
    */
    stage 'Crash on failed test'
    sh "cat ${resultsDir}/index.html | grep -q '<span class="test-result fail">' && exit 1"
  }

  stage 'Build'
  echo 'Building charms and uploading to store'
}
