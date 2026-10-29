# CrossMatch Browser v6.32.91 — GitHub source package & Windows Server deployment

**Scope:** This is the existing v6.32.91 application, prepared for source control. The matching engine, condition rules, and Excel exporter are **unchanged**. This is **not** evidence of a successful deployment to your server.

## 1. Choose the supported deployment target

The current Dockerfile builds a **Linux** `python:3.12-slim` container, with a Linux Nginx TLS proxy. **Docker Desktop is not supported on Windows Server 2022** ([Docker's Windows installation requirements](https://docs.docker.com/desktop/setup/install/windows-install/)). Do not install Docker Desktop on the server and expect an officially supported production stack.

**Recommended architecture:** Windows Server 2022 host → IT-managed Linux VM → Docker Engine + Docker Compose plugin → CrossMatch Web/Nginx. Verify server hardware/VM rights, network bridging/VLANs, firewall rules, organizational security approvals, and approved internal DNS/TLS with the server administrator. Alternatively, investigate a **native Windows Python service** + approved HTTPS reverse proxy. This source package does not implement or validate the latter; it is not a drop-in Windows Server container image.

## 2. Exact files to upload to a *private* GitHub repository

Extract `CrossMatch_Web_FAST_GitHub_Ready_v6.32.91.zip`. Open the **inside** `CrossMatch_Web_FAST` folder as repository root. Commit the application files at this level, including hidden `.gitignore`, `.dockerignore`, and `.env.example`:

- Root Python/config/build: `app.py`, `config.py`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `docker-compose.server.yml`, `reset_admin.py`.
- Source directories: **all** `engine/`, **all** `services/`, **all** `static/`, **all** `templates/`, **all** `nginx/`.
- Existing Windows 11 developer scripts: `CROSSMATCH_DOCKER_CONTROL.ps1`, `START_DOCKER.bat`, `STOP_DOCKER.bat`, `OPEN_APP.bat`, `GENERATE_SETUP_KEY.bat`, `GENERATE_SETUP_KEY.ps1`, `RESET_ADMIN.bat` (these are **not** Linux VM or Windows Server deployment scripts).
- Documentation and safe deployment helpers: `README.md`, `docs/`, `deploy/linux/`, `.gitignore`, `.dockerignore`, `.env.example`.

**Never commit** actual `.env`, user accounts/SQLite files and `database/`, `certificates/` or `.key`/`.pem` files, beneficiary Excel/CSV or ZIP exports, temporary sessions in `cache/`, uploads, results, backups, or logs. `.gitignore` helps only for future untracked files; it does **not** remove secrets already in Git history. For a pre-existing repository, check its history with the security team and rotate exposed credentials if any. Treat the source as internal agency intellectual property and obtain approval for use of GitHub, even in a private repository.

## 3. Upload using GitHub Desktop (Windows 11)

1. On GitHub, create a **Private** repository in your approved agency account/organization; avoid adding a README or license initially if you are uploading this complete source tree.
2. Extract the ZIP. Open **GitHub Desktop → File → Add local repository**. Choose the extracted `CrossMatch_Web_FAST` folder. If prompted that it is not a repository, choose **Create a Repository Here**.
3. Inspect the **Changes** tab. Confirm that `.env`, `database/`, `certificates/`, real datasets, and logs are **not** staged. If any sensitive file appears, stop and remove it from the staged commit before proceeding.
4. Commit the prepared source; use **Publish repository** and ensure **Keep this code private** is enabled. For an *existing* approved repo, use Repository → Repository settings / remote management, verifying the destination first.
5. In GitHub, verify the private visibility and source tree. Configure protected branches, least-privilege access and secret scanning/push protection where available.

**CLI alternative** (run in `CrossMatch_Web_FAST` folder, replacing the placeholder with your approved repository URL):

```bash
git init
git branch -M main
git add .gitignore .dockerignore .env.example README.md docs deploy app.py config.py requirements.txt Dockerfile docker-compose.yml docker-compose.server.yml reset_admin.py engine services static templates nginx *.bat *.ps1
git status --short
# REVIEW every staged file! Do not commit until it contains no secrets/PII.
git commit -m "Prepare CrossMatch Browser v6.32.91 source for private deployment"
git remote add origin <YOUR_APPROVED_PRIVATE_GITHUB_REPOSITORY_URL>
git push -u origin main
```

The wildcard patterns above are only for the known code files. If Git reports a missing pattern, stage those files by their explicit names. **Do not** use an unreviewed `git add .` on a directory containing beneficiary data.

## 4. First server deployment (IT-managed Linux VM)

Only after server and network/security approvals:

1. Install a maintained Linux distribution, Git, Docker Engine **and the Docker Compose plugin** on the VM. Use official distribution/Docker Engine guidance. Do not install Docker Desktop on the Windows Server host. Verify `docker version` and `docker compose version` in the VM.
2. Provision an approved internal DNS name and **CA-trusted** TLS certificate with a matching SAN. The Nginx container expects `certificates/server.crt` and `certificates/server.key`. The current Nginx image can create a localhost self-signed cert if files are absent, but **that is not a production certificate**. Provision real files before starting.
3. Clone the private repo to a fixed protected application path such as `/srv/crossmatch/CrossMatch_Web_FAST` using a **read-only deploy key** or your organization's approved credential manager. Avoid copying a developer's personal access token to the server.
4. Within that path, provision persistent `database/` and `certificates/` directories with restrictive ownership and permissions. **If migrating existing accounts**, restore a consistent backup of the original `database/` (including the SQLite WAL state if present); never initialize a fresh database over an existing one. The old `database` may contain users, saved rules, and audit logs.
5. Copy `.env.example` → `.env` **only on the server**. Restrict `chmod 600 .env`; set `CROSSMATCH_HTTPS_BIND_IP` to the **approved private VM IP**, `CROSSMATCH_COOKIE_SECURE=1`, and configure the first-admin `CROSSMATCH_SETUP_KEY` (generate using `openssl rand -hex 32`) only on a fresh install. Never post the key or `.env` to chat or GitHub. Preserve existing setup and account data on upgrades.
6. Protect `certificates/server.key` with restricted permissions and limit network connectivity to approved staff/VPN networks. The server Compose file intentionally publishes only HTTPS; the raw FastAPI port is not published. Port `18444` defaults to loopback until explicitly bound to the approved private IP.
7. Run the **read-only** preflight script and inspect the Compose configuration before starting:

```bash
cd /srv/crossmatch/CrossMatch_Web_FAST
sh deploy/linux/preflight.sh
docker compose -f docker-compose.server.yml config --quiet
docker compose -f docker-compose.server.yml up -d --build
# Do not run down -v; persistent database and named cache volume must survive.
docker compose -f docker-compose.server.yml ps
```

8. Check TLS certificate trust and `https://<APPROVED_INTERNAL_DNS>:18444/api/health` from an **authorized** workstation. Confirm `app_version` is **6.32.91** and review `/api/selftest` through the authenticated network. **Never bypass TLS checks in production.**
9. Verify first-admin setup (fresh install only), login, approval flow, sample CSV/XLSX, File A Only, File A vs File B, Sequential Process 1→2, Condition Builder, Keep One, and four-sheet Excel exports using **synthetic data**. Confirm File B stays reference-only. Confirm `Original File A = Validated + Duplicate + Review` before processing beneficiary information.
10. Configure uptime monitoring, restricted backups, disk usage alerts, patching, and access logs under IT policy. `CROSSMATCH_CACHE_ROOT` contains **temporary session uploads/results** on a named Docker volume with expiry; it is **not archival storage**. Maintain required approved retained outputs separately, and assess whether policy permits this workflow before production.

## 5. Code updates and rollback (do not reset application data)

Before changing code: complete all jobs, record the current Git commit and application health response, back up the persistent `database/`, `.env`, `certificates/` and any required named-volume data using an approved secure backup process. An SQLite database using WAL needs a **consistent** backup, preferably via the SQLite backup API or a quiesced service snapshot; don't just copy an active `.db` file without its WAL state.

With no active jobs and **after** the backup succeeds:

```bash
cd /srv/crossmatch/CrossMatch_Web_FAST
git status --short             # must be clean; never overwrite local edits blindly
git rev-parse HEAD             # record this rollback commit ID
git pull --ff-only            # use a pinned reviewed release or protected branch
docker compose -f docker-compose.server.yml up -d --build
# Inspect status/health and verify feature regression tests before admitting staff.
```

For rollback, after assessing database schema compatibility: check out the recorded **previous commit or release tag** to the same working directory, then rebuild the containers. **Keep** the persistent data mounts and the existing Compose project name unchanged. This rollback is safe only if no incompatible schema/data migration occurred; database restoration requires an approved backup. Never use `docker compose down -v`, `docker system prune --volumes`, or `git clean -fdx` in the live application directory.

## 6. Existing Windows 11 development workstation

Keep using `docker-compose.yml` and `START_DOCKER.bat` / `STOP_DOCKER.bat` as before. `docker-compose.server.yml` is a distinct Linux-VM deployment file. Do not run both Compose projects against the same database directory concurrently. Development and production must have separate credentials, data, TLS certs, network permissions and repository branches/releases.

## 7. Explicit limitations

- This package has **not** been pushed to a GitHub repository or deployed to a running Windows Server or Linux VM.
- No Docker daemon was available in the packaging environment, so `docker build` / actual Compose startup were **not run**. YAML, static code, archive membership and secret-exclusion checks were run locally.
- No agency security review, live TLS validation, dependency CVE scan, or 500K–1M record benchmark was performed. The Dockerfile uses floating base image tags and requires ongoing patch/image vulnerability scanning.
- Native Windows service deployment remains an **alternative to evaluate**, not a tested server installer.
- Private GitHub access is not equivalent to approval to host government beneficiary data there. **No beneficiary data belongs in the repository.**
