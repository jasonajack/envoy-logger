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
    stage('🐳 Build and push image') {
      when {
        branch('main')
      }
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
