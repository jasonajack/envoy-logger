def call(Map args) {
  def namespace = args.namespace
  def reponame = args.reponame
  def tagname = args.tagname

  Objects.requireNonNull(namespace)
  Objects.requireNonNull(reponame)
  Objects.requireNonNull(tagname)

  withCredentials([usernamePassword(credentialsId: 'docker-hub', usernameVariable: 'DOCKER_USERNAME', passwordVariable: 'DOCKER_PASSWORD')]) {
    sh(script: "docker login --username '${DOCKER_USERNAME}' --password '${DOCKER_PASSWORD}'")
    sh(script: "docker push docker.io/${namespace}/${reponame}:${tagname}")
  }
}
