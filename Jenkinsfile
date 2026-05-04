pipeline {
    agent any

    // ── Environment Variables ──────────────────────────────────────
    environment {
        DOCKER_IMAGE    = "seifchou/flask-devops-app"
        DOCKER_TAG      = "${BUILD_NUMBER}"          // unique tag per build
        FULL_IMAGE      = "${DOCKER_IMAGE}:${DOCKER_TAG}"
        APP_URL         = "http://flask-app.local"
        SONAR_PROJECT   = "flask-devops-app"
    }

    // ── Build Options ──────────────────────────────────────────────
    options {
        timeout(time: 30, unit: 'MINUTES')   // fail if pipeline takes >30min
        disableConcurrentBuilds()            // don't run two builds at once
    }

    stages {

        // ════════════════════════════════════════════════════════════
        // STAGE 1 — CHECKOUT
        // ════════════════════════════════════════════════════════════
        stage('Checkout') {
            steps {
                echo 'Checking out source code...'
                checkout scm    // download code from the repository configured in Jenkins
                sh 'ls -la'
                
                // Auto-update kubeconfig port from current cluster-info
                sh '''
                    PORT=$(kubectl cluster-info 2>/dev/null | grep "control plane" | grep -oP ":\\K[0-9]+")
                    if [ -n "$PORT" ]; then
                        sed -i "s/:[0-9]\\{4,5\\}$/:$PORT/" /var/jenkins_home/.kube/config
                        echo "✅ Kubeconfig updated to port $PORT"
                    fi
                '''
            }
        }

        // ════════════════════════════════════════════════════════════
        // STAGE 2 — INSTALL DEPENDENCIES
        // ════════════════════════════════════════════════════════════
        stage('Install Dependencies') {
            steps {
                echo '📦 Installing Python dependencies...'
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r app/requirements.txt
                    pip install -r app/requirements-dev.txt
                '''
            }
        }

        // ════════════════════════════════════════════════════════════
        // STAGE 3 — UNIT TESTS
        // ════════════════════════════════════════════════════════════
        stage('Unit Tests') {
            steps {
                echo '🧪 Running unit tests with coverage...'
                sh '''
                    . venv/bin/activate
                    cd app
                    python -m pytest test_app.py \
                        --cov=app \
                        --cov-report=xml:../coverage.xml \
                        --cov-report=term-missing \
                        --junit-xml=../test-results.xml \
                        -v
                '''
            }
            post {
                always {
                    // Archive test results so Jenkins displays them
                    junit allowEmptyResults: true, testResults: '**/test-results.xml'
                }
                failure {
                    echo '❌ Tests failed! Stopping pipeline.'
                }
            }
        }

        // ════════════════════════════════════════════════════════════
        // STAGE 4 — SONARQUBE ANALYSIS
        // ════════════════════════════════════════════════════════════
        stage('SonarQube Analysis') {
            steps {
                echo '🔍 Running SonarQube static analysis...'
                withSonarQubeEnv('SonarQube') {
                    // Use Jenkins-managed sonar scanner tool
                    withEnv(["PATH+SONAR=${tool 'sonar-scanner'}/bin"]) {
                        sh '''
                            sonar-scanner \
                            -Dsonar.projectKey=${SONAR_PROJECT} \
                            -Dsonar.sources=app \
                            -Dsonar.python.version=3.11 \
                            -Dsonar.python.coverage.reportPaths=coverage.xml
                        '''
                    }
                }
            }
        }

        // ════════════════════════════════════════════════════════════
        // STAGE 5 — SONARQUBE QUALITY GATE
        // Pipeline STOPS if code quality is too low
        // ════════════════════════════════════════════════════════════
        stage('Quality Gate') {
            steps {
                echo '🚦 Checking SonarQube Quality Gate...'
                timeout(time: 10, unit: 'MINUTES') {
                    // Jenkins fails the build if SonarQube says "FAILED"
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        // ════════════════════════════════════════════════════════════
        // STAGE 6 — DOCKER BUILD
        // ════════════════════════════════════════════════════════════
        stage('Docker Build') {
            steps {
                echo "🐳 Building Docker image: ${FULL_IMAGE}"
                sh "docker build -t ${FULL_IMAGE} -t ${DOCKER_IMAGE}:latest ."
                sh "docker images | grep flask-devops-app"
            }
        }

        // ════════════════════════════════════════════════════════════
        // STAGE 7 — TRIVY SECURITY SCAN
        // Scans the Docker image for known CVE vulnerabilities
        // ════════════════════════════════════════════════════════════
        stage('Trivy Image Scan') {
            steps {
                echo '🔒 Scanning Docker image for vulnerabilities...'
                sh '''
                    # Fail only on CRITICAL with available fixes
                    trivy image \
                        --exit-code 1 \
                        --severity CRITICAL \
                        --ignore-unfixed \
                        --format table \
                        --output trivy-report.txt \
                        ${FULL_IMAGE}

                    # Warn on HIGH (never fails build)
                    trivy image \
                        --exit-code 0 \
                        --severity HIGH \
                        --ignore-unfixed \
                        --format table \
                        ${FULL_IMAGE}
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'trivy-report.txt', allowEmptyArchive: true
                }
            }
        }

        // ════════════════════════════════════════════════════════════
        // STAGE 8 — DOCKER PUSH
        // ════════════════════════════════════════════════════════════
        stage('Docker Push') {
            steps {
                echo "📤 Pushing image to Docker Hub..."
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push ${FULL_IMAGE}
                        docker push ${DOCKER_IMAGE}:latest
                        echo "✅ Image pushed: ${FULL_IMAGE}"
                    '''
                }
            }
        }

        // ════════════════════════════════════════════════════════════
        // STAGE 9 — TERRAFORM (Infrastructure Provisioning)
        // Creates/updates Kubernetes namespaces
        // ════════════════════════════════════════════════════════════
        stage('Terraform Apply') {
            steps {
                echo '🌍 Provisioning infrastructure with Terraform...'
                dir('terraform') {
                    sh '''
                        terraform init \
                            -backend-config="path=/var/jenkins_home/terraform/terraform.tfstate"

                        terraform apply -auto-approve \
                            -state=/var/jenkins_home/terraform/terraform.tfstate
                    '''
                }
            }
        }

        // ════════════════════════════════════════════════════════════
        // STAGE 10 — ANSIBLE DEPLOY
        // Deploys the app to Kubernetes using the image we just built
        // ════════════════════════════════════════════════════════════
        stage('Ansible Deploy') {
            steps {
                echo "🚀 Deploying to Kubernetes with Ansible..."
                dir('ansible') {
                    sh """
                        # Pass the image tag as environment variable
                        export DOCKER_IMAGE=${FULL_IMAGE}
                        ansible-playbook playbook.yml \
                            -e "docker_image=${FULL_IMAGE}" \
                            -v
                    """
                }
            }
        }

        // ════════════════════════════════════════════════════════════
        // STAGE 11 — SMOKE TEST
        // Verifies the app is actually reachable after deployment
        // ════════════════════════════════════════════════════════════
        stage('Smoke Test') {
            steps {
                echo '💨 Running smoke test — checking app is reachable...'
                sh '''
                    # Forward the service port to localhost inside Jenkins
                    kubectl port-forward svc/flask-app-service 8888:80 -n flask-app &
                    PF_PID=$!

                    # Wait for port-forward to be ready
                    sleep 5

                    # Test the app
                    for i in $(seq 1 12); do
                        echo "Attempt $i/12..."
                        if curl -sf http://localhost:8888/health | grep -q "UP"; then
                            echo "✅ Smoke test PASSED!"
                            kill $PF_PID 2>/dev/null || true
                            exit 0
                        fi
                        sleep 5
                    done

                    kill $PF_PID 2>/dev/null || true
                    echo "❌ Smoke test FAILED!"
                    exit 1
                '''
            }
        }
    }

    // ── Post-Pipeline Actions ──────────────────────────────────────
    post {
        success {
            echo '''
               ✅ PIPELINE COMPLETED SUCCESSFULLY 
            '''
        }
        failure {
            echo '''
               ❌ PIPELINE FAILED                 
               Check logs above for details       
            '''
        }
        always {
            // Clean up Docker images to save disk space
            sh "docker rmi ${FULL_IMAGE} || true"
            cleanWs()    // clean workspace after each build
        }
    }
}
