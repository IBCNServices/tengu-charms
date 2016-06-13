node {
  echo 'Pipeline Start'
  stage 'Checkout'
  echo checkout scm

  stage 'Download Bigfiles'
  env.JUJU_REPOSITORY = pwd
  echo pwd
  echo env.JUJU_REPOSITORY
  sh 'tengu downloadbigfiles'
  stage 'Test'
  echo 'Stage Test'
}
