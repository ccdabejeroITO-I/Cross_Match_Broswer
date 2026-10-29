# Security and recovery checklist — CrossMatch v6.32.91

## Before committing to GitHub

- [ ] Approval to host the **source** in an organization-controlled **private** repo.
- [ ] Source and commit history checked for keys, credentials, personal records and sensitive internal endpoints.
- [ ] `.env`/`.env.*` (except `.env.example`), SQLite DBs/WAL, `database/`, `cache/`, `certificates/`, uploads, results, reports and backups absent from staged files.
- [ ] Personal developer access tokens are not in scripts or documentation.
- [ ] Repo access restricted to authorized personnel; secret scanning/push protection enabled where available.

## Before exposing the server to users

- [ ] Server OS/container strategy approved (Linux VM + Docker Engine recommended; no Docker Desktop on Windows Server).
- [ ] Linux VM isolated and patched; network firewall/VPN and internal DNS approved.
- [ ] TLS certificate and private key issued via organization PKI, protected, SAN matches internal DNS.
- [ ] Web only served through the HTTPS proxy; `CROSSMATCH_COOKIE_SECURE=1`; no direct FastAPI port exposed.
- [ ] Existing account DB restored and verified OR safe first-admin bootstrap configured.
- [ ] Backup verified recoverable, with data-access/audit controls and a defined recovery owner.
- [ ] Synthetic File A/ File B/ Sequential runs and correct four-sheet Excel tests complete.
- [ ] Identity/DOB checks and mandatory Review gates verified; rule templates not auto-enabled.
- [ ] Peak memory, storage headroom, cache retention, concurrency and access logs approved.

## Backups and rollback

- `database/` is the account/audit SQLite bind mount. Use a **consistent** SQLite backup, not an unsafe single-file copy of a running WAL-mode database.
- `certificates/` and private `.env` must be backed up **outside Git** with appropriate access controls.
- `crossmatch_fast_temp` is a **named Docker volume** containing temporary uploads/results. Check data-retention requirements; do not casually purge it.
- Before upgrades, finish active jobs, record `git rev-parse HEAD`, take verified backups, then deploy a reviewed commit.
- Rollback means return to the recorded commit and recreate containers **without deleting persistent volumes**; assess schema compatibility and restore from backups if necessary.

## Known operational risks to review before production

- Current Docker base images use version tags rather than immutable image digests. Perform dependency/container scans, maintenance and patching.
- Reverse proxy TLS settings use the application's existing Nginx config. A production security review should assess certificate chain, HSTS, proxy trust, authentication and authorized network exposure.
- Existing nginx startup creates a localhost self-signed certificate if none exists. Pre-provision your real certificate; do not rely on that fallback for staff access.
- App uploads and intermediate exports are placed under the cache volume and may expire; this is not a permanent beneficiary archive.
- The app's existing operational security and legal/policy compliance have **not** been independently certified by preparing this GitHub package.
