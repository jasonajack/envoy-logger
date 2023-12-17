def call(Map args) {
  def reponame = args.reponame
  def tagname = args.tagname
  withCredentials([usernamePassword(credentialsId: 'docker-hub', usernameVariable: 'DOCKER_USERNAME', passwordVariable: 'DOCKER_PASSWORD')]) {
    sh(script: "docker login --username '${DOCKER_USERNAME}' --password '${DOCKER_PASSWORD}'")
    sh(script: "docker push maniacmog/${reponame}:${tagname}")
  }
}
