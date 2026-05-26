# Security Policy

This document outlines the security policies, disclosure procedures, and compliance standards enforced within the UP Vidhan Sabha Election Ontology Engine codebase and infrastructure.

---

## Supported Versions

Only the current active release branch receives security patches and vulnerability remediation updates.

| Version | Supported | Security Patches |
| :--- | :--- | :--- |
| **v1.2.x** (Active) | Supported | Active Updates |
| **v1.1.x** | Unsupported | End of Support |
| **v1.0.x** | Unsupported | End of Support |

---

## Reporting a Vulnerability

As a strategic analysis platform, security and confidentiality are of paramount importance. Do not open public GitHub issues for security-sensitive bugs or vulnerability discoveries.

### Disclosure Process
1.  **Submit Vulnerability Report:** Email a detailed report directly to the security operations group at `security-ontology@election-engine.internal` or contact the administrator via secure channel.
2.  **Report Contents:**
    *   Description of the vulnerability.
    *   Step-by-step instructions to reproduce the issue (PoC scripts or request payloads).
    *   The potential impact (privilege escalation, SQL injection, data leakage).
3.  **Triage Timeline:** The security team will acknowledge receipt of the report within 24 hours and provide an initial assessment and timeline for remediation within 72 hours.
4.  **Patches Deployment:** Vulnerabilities will be addressed in a private repository branch and deployed directly to production. Once validated, security patches will be cherry-picked back into the active release branch.

---

## Compliance and Data Security Standards

The platform enforces data privacy compliance standards to protect candidate records, surveys, and demographic aggregates.

### 1. Electoral Roll Privacy
*   No personally identifiable information (PII) of voters is permitted in the database.
*   Electoral rolls are processed to generate anonymous booth-level demographic metrics (e.g., gender distribution counts and age brackets) before database insertion. Any raw PII documents must be purged from worker storage nodes after compilation.

### 2. Encryption Standards
*   **Transit Encryption:** All API calls, database connections (PostgreSQL/Neo4j), and worker connection requests must run over TLS 1.3.
*   **At-Rest Encryption:** Persistent disks hosting database instances must be encrypted using AES-256 at the block storage level.

### 3. API Hardening and Authentication
*   **Direct DB Isolation:** The PostgreSQL and Neo4j servers are bound strictly to localhost or private subnet IPs. External traffic must flow through the API gateway.
*   **PgBouncer Authentication:** The PgBouncer pooler acts as a firewall layer, managing transaction credentials and preventing Postgres connection slot exhaustion attacks.
*   **Rate Limiting:** Public endpoints are protected by rate limiters to prevent API scraping and denial-of-service attempts.
