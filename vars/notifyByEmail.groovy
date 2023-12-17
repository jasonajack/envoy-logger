def call() {
  emailext(attachLog: true, to: 'maniacmog@gmail.com', subject: '$DEFAULT_SUBJECT', body: '$DEFAULT_CONTENT')
}