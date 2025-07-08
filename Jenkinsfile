pipeline {
    agent any
    environment {
        DOCKER_REGISTRY = 'docker.io/ashnikh78' // e.g., docker.io/username
        DOCKER_IMAGE = "${DOCKER_REGISTRY}/restaurant-qa"
        DOCKER_TAG = "${env.BUILD_NUMBER}"
        DOCKER_CREDENTIALS_ID = 'b893f1a6-6692-426e-a60f-8fcef4279831' // Jenkins credentials ID
    }
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/ashnikh78/restaurant-qa..git'
            }
        }
        stage('Build') {
            steps {
                sh 'docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .'
            }
        }
        stage('Test') {
            steps {
                sh 'docker run --rm ${DOCKER_IMAGE}:${DOCKER_TAG} pytest src/tests/test_pipeline.py'
            }
        }
        stage('Push') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: "${DOCKER_CREDENTIALS_ID}",
                    usernameVariable: 'ashnikh78@gmail.com',
                    passwordVariable: 'Doc@80ld'
                )]) {
                    sh '''
                        echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin
                        docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                        docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest
                        docker push ${DOCKER_IMAGE}:latest
                    '''
                }
            }
        }
        stage('Deploy') {
            steps {
                sh '''
                    docker-compose down || true
                    docker-compose pull
                    docker-compose up -d
                '''
            }
        }
    }
    post {
        always {
            sh 'docker system prune -f'
        }
        success {
            slackSend(channel: '#deployments', message: "Restaurant QA build #${env.BUILD_NUMBER} deployed successfully!")
        }
        failure {
            slackSend(channel: '#deployments', message: "Restaurant QA build #${env.BUILD_NUMBER} failed!")
        }
    }
}