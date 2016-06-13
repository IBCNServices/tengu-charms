node {
  echo 'Pipeline Start'
  stage 'Checkout'
  echo checkout scm

  stage 'Download Bigfiles'
  env.JUJU_REPOSITORY = env.PWD
  echo env.PWD
  echo env.JUJU_REPOSITORY
  sh 'echo $PWD'
  stage 'Test'
  echo 'Stage Test'
}
