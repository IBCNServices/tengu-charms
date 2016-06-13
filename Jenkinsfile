node {
  echo 'Pipeline Start'
  stage 'Checkout'
  checkout scm

  stage 'Download Bigfiles'
  env.JUJU_REPOSITORY = env.PWD
  echo env.PWD
  echo env.JUJU_REPOSITORY
  stage 'Test'
  echo 'Stage Test'
}
