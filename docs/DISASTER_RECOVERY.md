# Disaster Recovery and Database Backups

This document outlines the backup policies, disaster recovery plans, and step-by-step restoration procedures for the PostgreSQL relational database, the Neo4j knowledge graph, and the Redis cache layer.

---

## Backup Schedules and Strategy

Production data is stored across distinct systems, each requiring dedicated backup routines.

| Database | Target Data | Backup Type | Frequency | Storage Location | Retention |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** | Fact tables, booth metrics, conversion funnels, chat logs | Logical snapshot (`pg_dump`) | Every 12 Hours | Encrypted S3 / Cloud Bucket | 30 Days |
| **Neo4j** | Graph structure, entity nodes, 5-layer intelligence relationships | Physical backup (`neo4j-admin database dump`) | Daily | Encrypted S3 / Cloud Bucket | 14 Days |
| **Redis** | Task queues, lock registries, active cache keys | RDB snapshotting (`dump.rdb`) | Hourly (Auto-save) | Local Persistent Volume | 24 Hours |

---

## PostgreSQL Backup and Restoration

### Logical Backup Execution
Execute backups of the relational database by targeting port `5432` directly, bypassing the PgBouncer pooler to avoid transaction locks or timeout terminations:

```bash
# Export the database schema and data into a compressed archive
pg_dump -h postgres-service -p 5432 -U postgres -d gorakhpur_db -F c -b -v -f /backups/postgres/gorakhpur_db_$(date +%F_%H%M).dump
```

### Complete Database Restoration
If database corruption or data loss occurs, restore using the following process:

1.  **Stop Ingestion and API Traffic:**
    Scale down API and worker replicas to prevent writing new data during restore:
    ```bash
    kubectl scale deployment/backend-api-deployment --replicas=0
    kubectl scale deployment/celery-workers-deployment --replicas=0
    ```
2.  **Terminate Active Pools:**
    Restart the PgBouncer service to close all persistent client sockets.
3.  **Perform Recovery Execution:**
    ```bash
    # Re-create database instance and load backup
    pg_restore -h postgres-service -p 5432 -U postgres -d gorakhpur_db -c -v --no-owner --no-privileges /backups/postgres/gorakhpur_db_target.dump
    ```
4.  **Restore Application Services:**
    Scale up deployments back to standard capacity:
    ```bash
    kubectl scale deployment/backend-api-deployment --replicas=3
    kubectl scale deployment/celery-workers-deployment --replicas=2
    ```

---

## Neo4j Graph Backup and Restoration

### Neo4j Database Dump
To take a clean snapshot of the Neo4j instance, the target database must be placed offline, or an online administrative command must be executed:

```bash
# Execute administrative dump command inside the Neo4j container
neo4j-admin database dump neo4j --to-path=/backups/neo4j/neo4j_graph_$(date +%F).dump
```

### Neo4j Database Restoration
Restoring a graph backup requires stopping the target database, loading the archive, and re-establishing constraints:

1.  **Stop the target database instance:**
    Connect to Neo4j Cypher Shell or Cypher Browser and execute:
    ```cypher
    STOP DATABASE neo4j;
    ```
2.  **Load the Dump Archive:**
    Execute the restore command inside the Neo4j container:
    ```bash
    neo4j-admin database load neo4j --from-path=/backups/neo4j/neo4j_graph_target.dump --overwrite-destination=true
    ```
3.  **Restart the database instance:**
    ```cypher
    START DATABASE neo4j;
    ```
4.  **Validate Graph Integrity:**
    Verify constraints and indices by running the loader schema integrity script:
    ```bash
    python -m pipeline.flows.graph.flow_load_graph --verify-only
    ```

---

## Redis Cache State Recovery

Redis functions as a task queue and transient cache. It runs with standard persistence enabled:

-   **RDB Persistence:** Enabled with configuration settings:
    `save 900 1` (saves if 1 key changes in 15 minutes)
    `save 300 10` (saves if 10 keys change in 5 minutes)
-   **Lock Recovery:** If the scraper locks are corrupted or stuck due to sudden termination, clear the lock keys manually to allow scrapers to resume:
    ```bash
    # Connect to redis-cli and remove the scraper locks
    redis-cli DEL lock:news_scraper
    redis-cli DEL lock:youtube_comments_scraper
    ```

---

## Post-Recovery Validation Checklist

After executing any database restoration, run these validation steps before routing external traffic to the API:

1.  **Check API Health status:** Verify that `/health` returns status `200` and passes PostgreSQL/Neo4j query validations.
2.  **Verify Row/Node counts:** Run the ontology status endpoint `/ontology/status` and ensure count values match historical telemetry metrics.
3.  **Run Ingestion Dry Run:** Trigger a small-batch news scraper task to confirm write/read pipelines to both databases are functional.
