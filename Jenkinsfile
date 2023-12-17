pipeline {
  agent {
    label 'workspace'
  }

  options {
    disableConcurrentBuilds()
    timestamps()
  }

  triggers {
    pollSCM('*/6 * * * *')
  }

  stages {
    when {
      branch('main')
    }
    stage('🐳 Build and push image') {
      steps {
        sh('./build_docker.sh latest')

        dockerPush(reponame: 'envoy_logger', tagname: 'latest')
      }
    }
  }

  post {
    failure {
      notifyByEmail()
    }

    cleanup {
      cleanWs()
    }
  }
}
