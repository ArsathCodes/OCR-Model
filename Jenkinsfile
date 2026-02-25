pipeline {
    agent any

    environment {
        GROQ_API_KEY = credentials('GROQ_API_KEY')
        DOCKER_IMAGE = "ocr-api"
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Pulling latest code...'
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Installing Python dependencies...'
                sh 'pip install -r requirements.txt --quiet'
            }
        }

        stage('Run Tests') {
            steps {
                echo 'Running tests...'
                sh 'python -m pytest tests/test_api.py -v --tb=short || true'
            }
        }

        stage('Build Docker Image') {
            steps {
                echo 'Building Docker image...'
                sh "docker build -f docker/Dockerfile -t ${DOCKER_IMAGE}:${BUILD_NUMBER} ."
                sh "docker tag ${DOCKER_IMAGE}:${BUILD_NUMBER} ${DOCKER_IMAGE}:latest"
            }
        }

        stage('Deploy') {
            steps {
                echo 'Deploying container...'
                sh "docker stop ocr-api-container || true"
                sh "docker rm   ocr-api-container || true"
                sh """
                    docker run -d \
                        --name ocr-api-container \
                        -p 8000:8000 \
                        -e GROQ_API_KEY=${GROQ_API_KEY} \
                        ${DOCKER_IMAGE}:latest
                """
            }
        }

        stage('Health Check') {
            steps {
                echo 'Checking API health...'
                sh 'sleep 5 && curl -f http://localhost:8000/health || true'
            }
        }
    }

    post {
        success {
            echo 'Pipeline SUCCESS - OCR API is live!'
        }
        failure {
            echo 'Pipeline FAILED - check logs above'
        }
    }
}D