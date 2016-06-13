


node {
  echo 'Pipeline Start'
  stage 'Checkout'
  checkout scm

  stage 'Download Bigfiles'
  env.JUJU_REPOSITORY = pwd()
  echo env.JUJU_REPOSITORY
  sh 'tengu downloadbigfiles'

  stage 'Test'
  sh 'bundletester -e tenguci -t /opt/tengu-charms/bundles/testbundle -l DEBUG --no-destroy'

  stage 'Build'
  echo 'Building charms and uploading to store'
}
