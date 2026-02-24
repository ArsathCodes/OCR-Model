pipeline {
    agent any

    environment {
        IMAGE_NAME    = "ocr-extraction-api"
        IMAGE_TAG     = "${BUILD_NUMBER}"
        GROQ_API_KEY  = credentials('GROQ_API_KEY')
        CONTAINER_NAME = "ocr-api"
        PORT          = "8000"
    }

    stages {

        stage('Checkout') {
            steps {
                echo '>>> Pulling latest code from GitLab...'
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                echo '>>> Installing Python dependencies...'
                sh '''
                    python3 -m pip install --upgrade pip
                    pip3 install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                echo '>>> Running API tests...'
                sh 'python3 -m pytest tests/ -v --tb=short || true'
            }
        }

        stage('Build Docker Image') {
            steps {
                echo '>>> Building Docker image...'
                sh '''
                    docker build -f docker/Dockerfile -t ${IMAGE_NAME}:${IMAGE_TAG} .
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest
                '''
            }
        }

        stage('Deploy Container') {
            steps {
                echo '>>> Deploying container...'
                sh '''
                    # Stop existing container if running
                    docker stop ${CONTAINER_NAME} || true
                    docker rm ${CONTAINER_NAME}   || true

                    # Start new container
                    docker run -d \
                        --name ${CONTAINER_NAME} \
                        -p ${PORT}:8000 \
                        -e GROQ_API_KEY=${GROQ_API_KEY} \
                        --restart unless-stopped \
                        ${IMAGE_NAME}:latest
                '''
            }
        }

        stage('Health Check') {
            steps {
                echo '>>> Verifying deployment...'
                sh '''
                    sleep 5
                    curl -f http://localhost:${PORT}/health || exit 1
                    echo "Deployment successful!"
                '''
            }
        }
    }

    post {
        success {
            echo "Build #${BUILD_NUMBER} deployed successfully!"
        }
        failure {
            echo "Build #${BUILD_NUMBER} failed!"
            sh 'docker logs ${CONTAINER_NAME} || true'
        }
    }
}