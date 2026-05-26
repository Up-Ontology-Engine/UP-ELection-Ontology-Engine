# Production Deployment Runbook

This document details the production deployment architecture, configuration parameters, and step-by-step rolling update workflows for the UP Vidhan Sabha Election Ontology Engine.

## Infrastructure Topology

The production architecture consists of four primary components deployed across isolated workloads:

1.  **Frontend Layer (Next.js):** Runs as a replicated client-side server utilizing Incremental Static Regeneration (ISR) to cache page reads at edge level, reducing downstream database request load.
2.  **API Layer (FastAPI):** Exposes transactional endpoints and serves request data. Connects to PostgreSQL exclusively via the PgBouncer pooler service.
3.  **Task Queue & Workers (Celery):** Executes periodic scrapers and heavy analytics tasks (data quality, scheme gaps, contradiction analysis, narrative engines). Connects to PostgreSQL via PgBouncer and uses Redis as a broker.
4.  **Database Layer (PostgreSQL & Neo4j):** PostgreSQL serves as the relational fact store; Neo4j maintains the 5-layer intelligence graph.

```
                  [ Ingress / ALB ]
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
 [ Next.js Frontend ]           [ FastAPI API Backend ]
   (Cached via ISR)                      │
                                         ▼
                               [ PgBouncer Pooler ] (Port 6432)
                                         │
                                         ▼
                               [ PostgreSQL Database ] (Port 5432)
                                         ▲
                                         │ (Direct Connection for Migrations)
                                 [ Alembic Runner ]
```

---

## Environment Variables Configuration

The following environment variables must be defined on the production target container environment. All credentials must be sourced from a secure vaults manager (e.g., Kubernetes Secrets or HashiCorp Vault).

### Relational Database
*   `DATABASE_URL`: Connection string pointing to the PgBouncer pooler. Format: `postgresql+asyncpg://<username>:<password>@pgbouncer-service:6432/gorakhpur_db`.
*   `MIGRATION_DATABASE_URL`: Connection string bypassing the pooler to execute schema DDL directly on PostgreSQL. Format: `postgresql://<username>:<password>@postgres-service:5432/gorakhpur_db`.

### Graph Database
*   `NEO4J_URI`: Connection endpoint for the Neo4j instance. Format: `bolt://neo4j-service:7687` or `neo4j://neo4j-service:7687`.
*   `NEO4J_USER`: Authentication username (default: `neo4j`).
*   `NEO4J_PASSWORD`: Production-grade password for Neo4j database authentication.

### Task Queue & Cache
*   `REDIS_URL`: Cache and message broker connection URL. Format: `redis://redis-service:6379/0`.
*   `CELERY_CONCURRENCY`: Number of concurrent Celery worker processes. Configured to `4` in production to optimize memory and connection footprints.

### Multilingual NLP & AI
*   `GROQ_API_KEY`: API credential key for LLM-based sentiment and semantic extraction (utilizes Llama 3.3 70B model).
*   `BHASHINI_USER_ID`: Authenticated User ID from the Bhashini Translation service portal.
*   `BHASHINI_API_KEY`: Translation API token key for Bhojpuri/Hindi conversions.
*   `SARVAM_API_KEY`: Key for the Sarvam AI translation/reasoning service (acts as the primary reasoning agent).
*   `GEMINI_API_KEY`: Fallback reasoning key when Sarvam requests exhaust rate limits.

---

## Kubernetes Deployment Model

Deployment to the Kubernetes cluster is managed via manifests under the `/k8s` directory. Rolling updates are deployed automatically via the CI/CD pipeline.

### Migration Safety & Startup Order
To prevent database connection drops and database schema misalignment, migrations must complete before any API instances start.

1.  **Init Containers:** The `backend-deployment.yaml` manifest defines an `initContainer` running the migration image.
2.  **DDL Execution:** The init container executes the shell command:
    ```bash
    alembic upgrade head
    ```
    This task bypasses PgBouncer and connects directly to port `5432` of the PostgreSQL cluster.
3.  **App Startup:** Only after the init container exits with status `0` will the primary FastAPI backend pods spin up and begin serving traffic via port `8000` through PgBouncer.

### Applying Manifests Manually
If manual deployment is required on the cluster, execute the following commands in sequence:

```bash
# 1. Apply configmaps and secrets containing environment settings
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml

# 2. Spin up Redis, PostgreSQL, and Neo4j stateful sets/services
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/neo4j-deployment.yaml
kubectl apply -f k8s/redis-deployment.yaml

# 3. Apply the PgBouncer pooler deployment and internal service
kubectl apply -f k8s/pgbouncer.yaml

# 4. Deploy the backend API services (this will run init container migrations)
kubectl apply -f k8s/backend-deployment.yaml

# 5. Deploy Celery workers and scheduler beats
kubectl apply -f k8s/celery-deployment.yaml

# 6. Apply Next.js frontend deployment
kubectl apply -f k8s/frontend-deployment.yaml
```

---

## Docker Compose Production Setup

For single-node staging environments, Docker Compose replicates the production network topology.

### Starting Staging Workloads
To boot the full stack in daemon mode with automated Grafana provisioning:

```bash
docker-compose -f docker-compose.yml up -d --build
```

### Verifying Service Health
Once started, verify container statuses:

```bash
docker-compose ps
```

All services, including `pgbouncer`, `prometheus`, and `grafana`, must report `healthy` or `running`. Check PgBouncer connection capabilities via the API health check logs:

```bash
docker logs backend-api-container
```

---

## Monitoring and Rolling Back

### Health Check Checks
The API exposes a highly responsive async health endpoint at `/health`. It validates database connectivity (both PostgreSQL and Neo4j) and cache status (Redis). Any pod returning a non-200 response code is automatically evicted from the ingress target pool by Kubernetes liveness probes.

### Rolling Back a Deployment
If anomalies or memory leaks are detected post-deployment, execute an immediate rollback of the deployment resource:

```bash
# Rollback API Backend
kubectl rollout undo deployment/backend-api-deployment

# Rollback Celery Workers
kubectl rollout undo deployment/celery-workers-deployment

# Monitor rollback progress
kubectl rollout status deployment/backend-api-deployment
```
