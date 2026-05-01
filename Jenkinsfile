pipeline {
    agent any

    // ── Environment Variables ──────────────────────────────────────
    environment {
        // Docker Hub image name — change 'yourdockerhub' to your username
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
                echo '📥 Checking out source code...'
                checkout scm    // pulls code from the Git repo
                sh 'ls -la'     // show what was checked out
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
                    // waitForQualityGate abortPipeline: true means
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
                    trivy image \
                        --exit-code 0 \
                        --severity HIGH,CRITICAL \
                        --format table \
                        --output trivy-report.txt \
                        ${FULL_IMAGE}

                    cat trivy-report.txt
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
                        terraform init

                        # Import existing namespaces into state (ignore errors if not exist yet)
                        terraform import kubernetes_namespace.app flask-app || true
                        terraform import kubernetes_namespace.monitoring monitoring || true

                        # Now apply — will update existing, create if missing
                        terraform apply -auto-approve
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
                    for i in $(seq 1 12); do
                        echo "Attempt $i/12..."
                        if curl -sf http://192.168.49.2/health -H "Host: flask-app.local" | grep -q "UP"; then
                            echo "✅ Smoke test PASSED! App is healthy."
                            exit 0
                        fi
                        sleep 5
                    done
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
            ╔══════════════════════════════════════╗
            ║   ✅ PIPELINE COMPLETED SUCCESSFULLY  ║
            ╚══════════════════════════════════════╝
            '''
        }
        failure {
            echo '''
            ╔══════════════════════════════════════╗
            ║   ❌ PIPELINE FAILED                  ║
            ║   Check logs above for details        ║
            ╚══════════════════════════════════════╝
            '''
        }
        always {
            // Clean up Docker images to save disk space
            sh 'docker image prune -f || true'
            cleanWs()    // clean workspace after each build
        }
    }
}
