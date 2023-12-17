library(identifier: '@main', retriever: legacySCM(scm)) _

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
        dockerBuild(
          namespace: 'maniacmog',
          reponame: 'envoy-logger',
          tagname: 'latest'
        )

        dockerPush(
          namespace: 'maniacmog',
          reponame: 'envoy-logger',
          tagname: 'latest'
        )
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
