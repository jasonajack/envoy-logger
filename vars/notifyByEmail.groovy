def call() {
  emailext(attachLog: true, to: 'jasonajack@gmail.com', subject: '$DEFAULT_SUBJECT', body: '$DEFAULT_CONTENT')
}