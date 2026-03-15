// =============================================================================
// LedgerWatch — Jenkinsfile
// =============================================================================
//
// JENKINS CONTAINER SETUP (one-time, before running this pipeline)
// ----------------------------------------------------------------
// Start Jenkins with the Docker socket mounted AND a named volume so that
// WORKSPACE paths are accessible to the host Docker daemon (required for
// the -v "${WORKSPACE}:/app" volume mounts used in Lint and Test stages):
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
        // On Docker Desktop the Jenkins container's WORKSPACE path is not directly
        // usable as a host volume mount. Set JENKINS_HOST_WORKSPACE in the Jenkins
        // node/agent config to the equivalent host path; falls back to WORKSPACE
        // for Linux agents where the paths are identical.
        HOST_WORKSPACE = "${env.JENKINS_HOST_WORKSPACE ?: env.WORKSPACE}"
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
        // The workspace is mounted read-only so no files can be modified.
        // Fails fast: any lint error aborts the pipeline before tests run.
        stage('Lint') {
            steps {
                sh """
                    docker run --rm \\
                        -v "${HOST_WORKSPACE}:/app:ro" -w /app \\
                        python:3.12-slim \\
                        sh -c "pip install --quiet 'ruff>=0.6,<0.7' && ruff check --no-cache ."
                """
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
                //    DB_HOST is the name of the postgres container — Docker's internal
                //    DNS resolves it because both containers share CI_NETWORK.
                sh """
                    docker run --rm \\
                        --network ${CI_NETWORK} \\
                        -v "${HOST_WORKSPACE}:/app" -w /app \\
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
            }

            post {
                always {
                    // Tear down CI resources regardless of pass/fail
                    sh "docker rm -f ${CI_DB} || true"
                    sh "docker network rm ${CI_NETWORK} || true"
                }
            }
        }

        // ── 4. Build Image ─────────────────────────────────────────────────────
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

        // ── 5. Run Migrations ──────────────────────────────────────────────────
        // Writes a temporary config/.env from Jenkins credentials so that
        // docker-compose can source it, then runs Django migrations.
        // The .env file is always deleted in post { always { } } below.
        stage('Run Migrations') {
            steps {
                // Ensure the compose postgres container is running
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
                sh 'docker compose up -d postgres'
                // Wait for postgres to be ready
                sh """
                    ready=0
                    for i in \$(seq 1 30); do
                        docker compose exec postgres pg_isready -U ledger -d ledgerwatch && ready=1 && break || true
                        echo "  postgres not ready yet (\$i/30)..."
                        sleep 2
                    done
                    if [ "\$ready" -eq 0 ]; then
                        echo "ERROR: compose postgres did not become ready after 60 s"
                        exit 1
                    fi
                """
                sh """
                    docker run --rm \\
                        --network ${COMPOSE_PROJECT_NAME}_default \\
                        -e SECRET_KEY="${SECRET_KEY}" \\
                        -e DEBUG=False \\
                        -e ALLOWED_HOSTS=localhost,127.0.0.1 \\
                        -e DB_NAME=ledgerwatch \\
                        -e DB_USER=ledger \\
                        -e DB_PASSWORD="${DB_PASSWORD}" \\
                        -e DB_HOST=postgres \\
                        -e DB_PORT=5432 \\
                        ${IMAGE_NAME}:${BUILD_NUMBER} \\
                        python manage.py migrate --noinput
                """
            }
        }

        // ── 6. Deploy ──────────────────────────────────────────────────────────
        // Brings up (or restarts) the full stack with the freshly-built image.
        // docker compose up -d is idempotent: running containers are left alone,
        // only containers whose image changed are recreated.
        stage('Deploy') {
            steps {
                sh "docker compose up -d --no-build"
                echo "Deployed — API: http://localhost:8000 | Docs: http://localhost:8000/api/docs/"
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
