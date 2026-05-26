# Operational Troubleshooting Runbooks

This document contains step-by-step procedures to triage and resolve common operational alerts in production environments.

---

## 1. PgBouncer Connection Pool Exhaustion

### Symptom
Application logs return errors such as:
- `FATAL: remaining connection slots are reserved for non-replication superuser connections`
- `PgBouncer: query timeout / connection limit reached`

### Diagnostic Steps
1.  **Check PgBouncer Statistics:**
    Connect directly to the PgBouncer administrative console:
    ```bash
    psql -h pgbouncer-service -p 6432 -U pgbouncer pgbouncer
    ```
    Execute stats commands:
    ```sql
    SHOW POOLS;
    SHOW CLIENTS;
    ```
    Identify if `cl_active` (active clients) equals the maximum connection limit, or if `sv_active` (server connections) is fully saturated.
2.  **Locate Database Connection Leaks:**
    Connect directly to PostgreSQL (port `5432`) and check active connections:
    ```sql
    SELECT pid, usename, client_addr, state, query 
    FROM pg_stat_activity 
    WHERE state != 'idle';
    ```
    Identify if there are unclosed async connections from old Celery worker tasks.

### Resolution Steps
-   **If Celery workers are leaking connections:**
    Force restart Celery containers to clear sockets:
    ```bash
    kubectl rollout restart deployment/celery-workers-deployment
    ```
-   **Modify PgBouncer Limits:**
    If legitimate traffic exceeds connection limits, edit the PgBouncer configurations in `docker-compose.yml` or the Kubernetes ConfigMap:
    ```ini
    # Increase maximum clients and pool size limits
    max_client_conn = 500
    default_pool_size = 50
    ```
    Reload PgBouncer config without dropping connections:
    ```sql
    -- In PgBouncer console
    RELOAD;
    ```

---

## 2. LLM / Translation API Throttling (HTTP 429 Rate Limits)

### Symptom
Ingestion pipelines and NLP runs fail, returning:
- `HTTPException: 429 Too Many Requests`
- Groq or Bhashini rate limit warnings in logging files.

### Diagnostic Steps
Identify which service is throttled:
-   **Groq API:** Check headers in the response payload logs (`x-ratelimit-remaining-tokens`, `x-ratelimit-reset-requests`).
-   **Bhashini API:** Verify token allocations in Bhashini console logs.

### Resolution Steps
1.  **Reduce NLP Pipeline Batch Sizes:**
    Edit the production environment variable parameters in `configmap.yaml` or `.env` to lower processing speeds:
    ```ini
    NLP_BATCH_SIZE=10
    ```
2.  **Introduce Extraction Delays:**
    Add a sleep parameter inside `pipeline/nlp/extractor.py` to pace the requests:
    ```python
    import time
    time.sleep(1.0) # Introduce 1-second delay between sequential API requests
    ```
3.  **Activate Fallback Configurations:**
    If Bhashini is rate-limited, verify that Bhashini translates fallback to local translation models correctly. If Sarvam is exhausted, verify that `GEMINI_API_KEY` is present to support automatic model fallback.

---

## 3. Redis Cache Saturation or Stuck Locks

### Symptom
- Scrapers complete instantly without executing tasks.
- FastAPI responses feel sluggish or Redis reports `OOM command not allowed when used memory > 'maxmemory'`.

### Diagnostic Steps
1.  **Verify Memory Consumption:**
    Connect to redis-cli and check stats:
    ```bash
    redis-cli -h redis-service info memory
    ```
    Verify if `used_memory_human` approaches the container allocations limit.
2.  **Verify Scraper Lock Status:**
    Identify if scraper lock keys are stuck:
    ```bash
    redis-cli -h redis-service KEYS "lock:*"
    ```

### Resolution Steps
-   **If a scraper lock is stuck after container crash:**
    Delete the specific lock key to allow ingestion tasks to execute:
    ```bash
    redis-cli -h redis-service DEL lock:news_scraper
    ```
-   **If Redis memory is exhausted:**
    Modify the eviction policy configuration inside the Redis config map:
    ```ini
    maxmemory-policy allkeys-lru
    ```
    Alternatively, clear temporary API response caches manually:
    ```bash
    redis-cli -h redis-service FLUSHDB
    ```

---

## 4. Neo4j Out of Memory (OOM)

### Symptom
- Neo4j logs return `OutOfMemoryError: Java heap space`.
- Container crashes or reports unhealthy status under heavy graph loading runs.

### Diagnostic Steps
Check the Neo4j query logs for unoptimized queries (e.g., cartesian products):
```bash
docker logs gorakhpur_neo4j | grep -i "oom"
```

### Resolution Steps
1.  **Scale Memory Allocations:**
    Adjust Java heap bounds in `docker-compose.yml` or `neo4j-deployment.yaml`:
    ```yaml
    NEO4J_server_memory_heap_initial__size: 2G
    NEO4J_server_memory_heap_max__size: 4G
    NEO4J_server_memory_pagecache_size: 2G
    ```
2.  **Clear Unoptimized Queries:**
    Restart the Neo4j instance to clear memory overhead:
    ```bash
    kubectl rollout restart deployment/neo4j-deployment
    ```
