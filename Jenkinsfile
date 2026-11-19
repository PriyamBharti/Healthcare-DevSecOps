pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        IMAGE_NAME = 'healthcare-devsecops'
        APP_CONTAINER = 'healthcare-devsecops-jenkins'
        APP_PORT = '5002'
    }

    stages {

        stage('Checkout Source Code') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .'
            }
        }

        stage('Deploy Healthcare Website') {
            steps {
                withCredentials([
                    string(
                        credentialsId: 'healthcare-jwt-secret',
                        variable: 'JWT_SECRET'
                    )
                ]) {
                    sh '''
                        set -eu

                        docker volume create healthcare-devsecops-jenkins-data

                        docker rm -f "$APP_CONTAINER" >/dev/null 2>&1 || true

                        docker run -d \
                            --name "$APP_CONTAINER" \
                            --restart unless-stopped \
                            -p "$APP_PORT:5000" \
                            -e JWT_SECRET_KEY="$JWT_SECRET" \
                            -e DATABASE_URL=sqlite:////data/healthcare.db \
                            --mount source=healthcare-devsecops-jenkins-data,target=/data \
                            "$IMAGE_NAME:$BUILD_NUMBER"
                    '''
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                sh '''
                    set -eu

                    for attempt in 1 2 3 4 5 6 7 8 9 10; do
                        if docker exec "$APP_CONTAINER" python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3).read().decode())"; then
                            exit 0
                        fi

                        sleep 2
                    done

                    docker logs "$APP_CONTAINER"
                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo 'Healthcare application deployed successfully!'
        }

        failure {
            echo 'Deployment failed. Check the Jenkins Console Output.'
        }
    }
}