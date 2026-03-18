// =============================================================================
// LedgerWatch — Jenkinsfile
// =============================================================================
//
// JENKINS CONTAINER SETUP (one-time, before running this pipeline)
// ----------------------------------------------------------------
// Start Jenkins with the Docker socket mounted:
//
//   docker run -d \
//     --name jenkins \
//     -p 8080:8080 \
//     -p 50000:50000 \
//     -v /var/run/docker.sock:/var/run/docker.sock \
//     -v jenkins_home:/var/jenkins_home \
//     jenkins/jenkins:lts-jdk17
//
// Then install Docker CLI and Compose plugin inside the Jenkins container:
//
//   docker exec -u root jenkins \
//     bash -c "apt-get update && apt-get install -y docker.io docker-compose-plugin"
//
//   docker exec -u root jenkins usermod -aG docker jenkins
//   docker restart jenkins
//
// JENKINS CREDENTIALS  (Manage Jenkins → Credentials → Global → Add Credential)
// -------------------------------------------------------------------------------
//   ID: LEDGERWATCH_SECRET_KEY   Kind: Secret text   Value: a long random string
//   ID: LEDGERWATCH_DB_PASSWORD  Kind: Secret text   Value: postgres password
//
// =============================================================================

pipeline {
    agent any

    environment {
        IMAGE_NAME          = 'ledgerwatch'
        // Set COMPOSE_PROJECT_NAME explicitly so the compose network name is
        // always predictable (${COMPOSE_PROJECT_NAME}_default).
        COMPOSE_PROJECT_NAME = 'ledgerwatch'
        // Unique names per build so parallel/re-run builds never collide
        CI_NETWORK   = "ledgerwatch-ci-${BUILD_NUMBER}"
        CI_DB        = "ledgerwatch-db-${BUILD_NUMBER}"
        TEST_DB_NAME = 'ledgerwatch_test'
        TEST_DB_USER = 'ledger'
        // Credentials are masked in logs; values injected from Jenkins credential store
        SECRET_KEY   = credentials('LEDGERWATCH_SECRET_KEY')
        DB_PASSWORD  = credentials('LEDGERWATCH_DB_PASSWORD')
    }

    options {
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {

        // ── 1. Checkout ────────────────────────────────────────────────────────
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // ── 2. Lint ────────────────────────────────────────────────────────────
        // Runs ruff inside a throw-away python:3.12-slim container.
        // Uses docker cp instead of bind mounts so this works reliably in
        // Docker-in-Docker setups (e.g. Jenkins in a container on Docker Desktop).
        // Fails fast: any lint error aborts the pipeline before tests run.
        stage('Lint') {
            steps {
                sh """
                    docker create --name lint-${BUILD_NUMBER} \\
                        -w /app \\
                        python:3.12-slim \\
                        sh -c "pip install --quiet 'ruff>=0.6,<0.7' && ruff check --no-cache ."
                """
                sh """docker cp "${WORKSPACE}/." lint-${BUILD_NUMBER}:/app/"""
                sh "docker start -a lint-${BUILD_NUMBER}"
            }
            post {
                always {
                    sh "docker rm -f lint-${BUILD_NUMBER} || true"
                }
            }
        }

        // ── 3. Test ────────────────────────────────────────────────────────────
        // Spins up an isolated Docker network + a throw-away PostgreSQL container,
        // then runs pytest inside a python:3.12-slim container on the same network
        // so it can reach postgres by container name.
        // The network and DB container are always removed in post { always { } }.
        stage('Test') {
            steps {
                // 1. Create an isolated bridge network for this build
                sh "docker network create ${CI_NETWORK}"

                // 2. Start a throw-away PostgreSQL container on that network
                sh """
                    docker run -d \\
                        --name ${CI_DB} \\
                        --network ${CI_NETWORK} \\
                        -e POSTGRES_DB=${TEST_DB_NAME} \\
                        -e POSTGRES_USER=${TEST_DB_USER} \\
                        -e POSTGRES_PASSWORD="${DB_PASSWORD}" \\
                        postgres:16-alpine
                """

                // 3. Wait until PostgreSQL is accepting connections (up to 60 s)
                sh """
                    ready=0
                    for i in \$(seq 1 30); do
                        docker exec ${CI_DB} \\
                            pg_isready -U ${TEST_DB_USER} -d ${TEST_DB_NAME} \\
                            && ready=1 && break || true
                        echo "  postgres not ready yet (\$i/30), retrying in 2 s..."
                        sleep 2
                    done
                    if [ "\$ready" -eq 0 ]; then
                        echo "ERROR: postgres (${CI_DB}) did not become ready after 60 s"
                        exit 1
                    fi
                """

                // 4. Install dependencies and run the full test suite.
                //    Uses docker cp instead of bind mounts (Docker-in-Docker safe).
                //    DB_HOST is the name of the postgres container — Docker's internal
                //    DNS resolves it because both containers share CI_NETWORK.
                sh """
                    docker create --name test-runner-${BUILD_NUMBER} \\
                        --network ${CI_NETWORK} \\
                        -w /app \\
                        -e SECRET_KEY="${SECRET_KEY}" \\
                        -e DEBUG=True \\
                        -e ALLOWED_HOSTS=localhost \\
                        -e DB_NAME=${TEST_DB_NAME} \\
                        -e DB_USER=${TEST_DB_USER} \\
                        -e DB_PASSWORD="${DB_PASSWORD}" \\
                        -e DB_HOST=${CI_DB} \\
                        -e DB_PORT=5432 \\
                        python:3.12-slim \\
                        sh -c " \\
                            apt-get update -qq \\
                            && apt-get install -y -qq libpq-dev gcc \\
                            && pip install --quiet -r requirements.txt \\
                            && pytest --tb=short \\
                        "
                """
                sh """docker cp "${WORKSPACE}/." test-runner-${BUILD_NUMBER}:/app/"""
                sh "docker start -a test-runner-${BUILD_NUMBER}"
            }

            post {
                always {
                    // Tear down CI resources regardless of pass/fail
                    sh "docker rm -f test-runner-${BUILD_NUMBER} || true"
                    sh "docker rm -f ${CI_DB} || true"
                    sh "docker network rm ${CI_NETWORK} || true"
                }
            }
        }

        // ── 4. Frontend Install ────────────────────────────────────────────────
        // Installs frontend dependencies inside a node:20 container.
        stage('Frontend Install') {
            steps {
                sh """
                    docker create --name fe-install-${BUILD_NUMBER} \\
                        -w /app \\
                        node:20-alpine \\
                        sh -c "npm ci"
                """
                sh """docker cp "${WORKSPACE}/frontend/." fe-install-${BUILD_NUMBER}:/app/"""
                sh "docker start -a fe-install-${BUILD_NUMBER}"
                sh """rm -rf "${WORKSPACE}/frontend/node_modules" """
                sh """docker cp fe-install-${BUILD_NUMBER}:/app/node_modules "${WORKSPACE}/frontend/node_modules" """
            }
            post {
                always {
                    sh "docker rm -f fe-install-${BUILD_NUMBER} || true"
                }
            }
        }

        // ── 5. Frontend Lint ───────────────────────────────────────────────────
        stage('Frontend Lint') {
            steps {
                sh """
                    docker create --name fe-lint-${BUILD_NUMBER} \\
                        -w /app \\
                        node:20-alpine \\
                        sh -c "npx eslint src/"
                """
                sh """docker cp "${WORKSPACE}/frontend/." fe-lint-${BUILD_NUMBER}:/app/"""
                sh "docker start -a fe-lint-${BUILD_NUMBER}"
            }
            post {
                always {
                    sh "docker rm -f fe-lint-${BUILD_NUMBER} || true"
                }
            }
        }

        // ── 6. Frontend Test ───────────────────────────────────────────────────
        stage('Frontend Test') {
            steps {
                sh """
                    docker create --name fe-test-${BUILD_NUMBER} \\
                        -w /app \\
                        node:20-alpine \\
                        sh -c "npx vitest run --passWithNoTests"
                """
                sh """docker cp "${WORKSPACE}/frontend/." fe-test-${BUILD_NUMBER}:/app/"""
                sh "docker start -a fe-test-${BUILD_NUMBER}"
            }
            post {
                always {
                    sh "docker rm -f fe-test-${BUILD_NUMBER} || true"
                }
            }
        }

        // ── 7. Frontend Build ──────────────────────────────────────────────────
        stage('Frontend Build') {
            steps {
                sh """
                    docker create --name fe-build-${BUILD_NUMBER} \\
                        -w /app \\
                        node:20-alpine \\
                        sh -c "npm run build"
                """
                sh """docker cp "${WORKSPACE}/frontend/." fe-build-${BUILD_NUMBER}:/app/"""
                sh "docker start -a fe-build-${BUILD_NUMBER}"
            }
            post {
                always {
                    sh "docker rm -f fe-build-${BUILD_NUMBER} || true"
                }
            }
        }

        // ── 8. Build Image ─────────────────────────────────────────────────────
        // Builds the production Docker image and tags it with both the build
        // number (immutable, for rollback) and 'latest' (for docker-compose).
        stage('Build Image') {
            steps {
                sh """
                    docker build \\
                        -t ${IMAGE_NAME}:${BUILD_NUMBER} \\
                        -t ${IMAGE_NAME}:latest \\
                        -f docker/Dockerfile .
                """
            }
        }

        // ── 9. Deploy ─────────────────────────────────────────────────────────
        // Writes a temporary config/.env from Jenkins credentials, then brings
        // up the full stack. The api container's entrypoint runs migrations
        // automatically before starting gunicorn.
        stage('Deploy') {
            steps {
                script {
                    writeFile file: 'config/.env', text: [
                        "SECRET_KEY=${env.SECRET_KEY}",
                        "DEBUG=False",
                        "ALLOWED_HOSTS=localhost,127.0.0.1",
                        "DB_NAME=ledgerwatch",
                        "DB_USER=ledger",
                        "DB_PASSWORD=${env.DB_PASSWORD}",
                        "DB_HOST=postgres",
                        "DB_PORT=5432",
                    ].join('\n') + '\n'
                }
                sh "docker compose -f docker-compose.yml up -d --build"
                echo "Deployed — App: http://localhost | API: http://localhost:8000 | Docs: http://localhost:8000/api/docs/"
            }
        }
    }

    post {
        always {
            // config/.env must never be left on disk between builds
            sh 'rm -f config/.env || true'
        }
        success {
            echo "Build ${BUILD_NUMBER} passed. Image tagged ${IMAGE_NAME}:${BUILD_NUMBER}."
        }
        failure {
            echo "Build ${BUILD_NUMBER} failed. Check the stage logs above."
        }
    }
}
