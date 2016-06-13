node {
  echo 'Pipeline Start'
  stage 'Checkout'
  checkout scm

  stage 'Download Bigfiles'
  env.JUJU_REPOSITORY = pwd()
  echo env.JUJU_REPOSITORY
  sh 'tengu downloadbigfiles'

  stage 'Test'
  echo 'Stage Test'
}
