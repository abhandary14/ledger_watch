# Running the Jenkins Pipeline Locally

LedgerWatch uses two CI systems with separate jobs:

- **GitHub Actions** (`.github/workflows/ci.yml`) runs lint and tests on every push and pull request to `main`, `staging`, `dev-backend` and `dev-frontend`. It is the check that gates merges.
- **Jenkins** (`Jenkinsfile`) is the build-and-deploy pipeline. It lints, tests and builds every branch, but **only deploys `main`**.

This guide sets up Jenkins in a local Docker container and runs the pipeline against the GitHub repository.

## Prerequisites

- Docker Desktop (or Docker Engine) running.
- Ports **8080** (Jenkins), **80**, **8000** and **5433** free. If you are running the app in development mode, stop it first (`Ctrl+C` on `runserver` / `npm run dev`, then `docker compose stop postgres`).

> On Windows, run these commands in **PowerShell**. Git Bash rewrites paths like `/var/run/docker.sock` into Windows paths and breaks them (or prefix each command with `MSYS_NO_PATHCONV=1`).

## 1. Start Jenkins

```bash
docker run -d --name jenkins -p 8080:8080 -p 50000:50000 -v /var/run/docker.sock:/var/run/docker.sock -v jenkins_home:/var/jenkins_home jenkins/jenkins:lts-jdk17
```

## 2. Give Jenkins the Docker CLI, Compose and Buildx

The pipeline runs `docker` and `docker compose` from inside the Jenkins container, against the host's Docker daemon.

```bash
docker exec -u root jenkins bash -c "apt-get update && apt-get install -y docker.io"

docker exec -u root jenkins bash -c "mkdir -p /usr/local/lib/docker/cli-plugins && curl -fSL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose && chmod +x /usr/local/lib/docker/cli-plugins/docker-compose"

docker exec -u root jenkins bash -c "curl -fSL https://github.com/docker/buildx/releases/download/v0.17.1/buildx-v0.17.1.linux-amd64 -o /usr/local/lib/docker/cli-plugins/docker-buildx && chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx"

docker exec -u root jenkins usermod -aG docker jenkins
docker restart jenkins
```

Compose and Buildx are installed directly because the Debian packages available in the Jenkins image are missing (`docker-compose-plugin`) or too old (Buildx must be 0.17.0+ for `docker compose up --build`).

Verify:

```bash
docker exec jenkins docker compose version
docker exec jenkins docker buildx version
```

If either reports `permission denied ... docker.sock` (common on Docker Desktop), allow access for this local setup and re-check:

```bash
docker exec -u root jenkins chmod 666 /var/run/docker.sock
```

These tools live inside the container: they survive `docker restart jenkins` but not `docker rm jenkins`. Job configuration is kept in the `jenkins_home` volume.

## 3. First-time Jenkins setup

1. Open http://localhost:8080.
2. Unlock with the password from:
   ```bash
   docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
   ```
3. Choose **Install suggested plugins** and create an admin user.
4. Set **Manage Jenkins → Nodes → Built-In Node → Configure → Number of executors** to `1`.
   Container and network names in the pipeline include the build number, which is counted per branch — two branches building at once would collide.

## 4. Add credentials

**Manage Jenkins → Credentials → System → Global credentials → Add Credentials**, kind **Secret text**:

| ID | Value |
|---|---|
| `LEDGERWATCH_SECRET_KEY` | A random string, e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `LEDGERWATCH_DB_PASSWORD` | Any password |

The first `main` deploy initialises the deployed database with this password. Changing it later requires deleting the deployed database volume (see [Clean up](#7-clean-up)).

Jenkins masks credential values everywhere in build logs, so avoid values that also appear as names (e.g. `ledgerwatch`).

## 5. Create the job

1. **New Item** → name `ledger-watch` → **Multibranch Pipeline**.
   A plain *Pipeline* job won't work: the Deploy stage's `when { branch 'main' }` needs `BRANCH_NAME`, which only multibranch jobs set.
2. **Branch Sources → Add source → Git**, repository `https://github.com/abhandary14/ledger_watch.git` (public — no credentials needed).
3. **Build Configuration:** by Jenkinsfile, script path `Jenkinsfile`.
4. **Save.** Jenkins scans the repository and builds every branch.

Builds run when you click **Scan Multibranch Pipeline Now** (or **Build Now** on a branch). For automatic builds, enable *Scan Multibranch Pipeline Triggers → Periodically if not otherwise run* — GitHub can't send webhooks to a Jenkins on your machine.

## 6. Verify

The pipeline stages are: Checkout → Lint → Test → Frontend Install → Frontend Lint → Frontend Test → Frontend Build → Build Image → Deploy.

- **Non-`main` branches:** all stages pass and **Deploy is skipped** ("skipped due to when conditional").
- **`main`:** all stages pass, including Deploy. Then check:
  - http://localhost — the app
  - http://localhost:8000/health — `{"status": "ok"}`
  - http://localhost:8000/api/docs/ — API docs

To add data, register an organization at http://localhost, then seed it (the `--org` name must match exactly, including case):

```bash
docker compose -p ledgerwatch exec api python manage.py seed_transactions --org "<your org name>"
```

The deployment's Compose project is `ledgerwatch`, so its database volume (`ledgerwatch_postgres_data`) is separate from the development database.

## 7. Clean up

```bash
docker compose -p ledgerwatch stop      # stop the deployed app (start again with: start)
docker compose -p ledgerwatch down      # remove its containers (add -v to delete its database)
docker stop jenkins                     # stop Jenkins (start again with: docker start jenkins)
```

The deployed containers use `restart: unless-stopped`, so they start with Docker unless stopped. Stop them before running the app in development mode, which needs ports 5433 and 8000.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `mkdir C:\Program Files\Git\var: Access is denied` | You ran the command in Git Bash — use PowerShell or `MSYS_NO_PATHCONV=1`. |
| `compose build requires buildx 0.17.0 or later` | Install Buildx (step 2). |
| `permission denied ... /var/run/docker.sock` | `docker exec -u root jenkins chmod 666 /var/run/docker.sock` |
| Deploy fails with `port is already allocated` | Stop the development database / servers (see Prerequisites). |
| Deploy never runs on `main` | The job isn't a Multibranch Pipeline. |
