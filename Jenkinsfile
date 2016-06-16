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
  // workaround for https://bugs.launchpad.net/juju/+bug/1592822
  sh 'rm charms/trusty/rest2jfed/files/jfedS4/jfed_cli.tar.gz'
  sh 'rm charms/trusty/rest2jfed/files/jdk-8u77-linux-x64.tar.gz'
  /*
    The next stage assumes that `charm login` is already executed and access is
    granted to the channels:

        charm grant cs:~tengu-bot/trusty/hauchiwa everyone --channel development
        charm grant cs:~tengu-bot/trusty/rest2jfed everyone --channel development
  */
  stage 'Push Charms'
  def urls = []
  sh("( charm push charms/trusty/hauchiwa || exit 1 ) | grep '^url:' | sed -r 's/^.{5}//' > result")
  urls.add(readFile('result').trim()) //workaround for https://issues.jenkins-ci.org/browse/JENKINS-26133
  sh("( charm push charms/trusty/rest2jfed || exit 1 ) | grep '^url:' | sed -r 's/^.{5}//' > result")
  urls.add(readFile('result').trim()) //workaround for https://issues.jenkins-ci.org/browse/JENKINS-26133
  //urls.add('cs:~tengu-bot/rest2jfed-2')
  //urls.add('cs:~tengu-bot/hauchiwa-3')
  sh "./cihelpers.py replace ${pwd()}/bundles/hauchiwa-testbundle/bundle.yaml ${urls.join(' ')}"
  echo "Urls are:\n ${urls.join('\t\n')}"
  sh("./cihelpers.py publish development ${urls.join(' ')}")

  try {
    /*
      run tests according to testplan in repo root.
    */
    stage 'Test'
    echo 'before'

    echo 'after'
    sh "cwr --no-destroy tenguci testplan.yaml --no-destroy -l DEBUG -o ${resultsDir}"
  } finally {
    /*
      publish test results even when tests failed. apache2 needs to be
      installed for this to work. Default apache2 config is ok.
    */
    stage 'Publish Test results'
    sh "cp `ls -dt ${resultsDir}/* | grep result.html | head -1` ${resultsDir}/index.html"
    sh "cp `ls -dt ${resultsDir}/* | grep result.json | head -1` ${resultsDir}/index.json"

    /*
      this is here so the "Publish Test results" stage doesn't appear 'crashed'
      when the "Test" stage crashed
    */
    stage 'Crash on failed test'
    sh "cat ${resultsDir}/index.json | grep -q '\"test_outcome\": \"All Passed\"'"
  }

  stage 'Publish'
  echo 'Publish Charms to the store in stable'
  sh("./cihelpers.py publish stable ${urls.join(' ')}")
}
