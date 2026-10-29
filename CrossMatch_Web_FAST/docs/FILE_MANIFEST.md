# GitHub upload manifest — CrossMatch Browser v6.32.91

This list is extracted from the prepared source folder, not an assumed project template. **Upload this directory at the repository root (not the containing release ZIP).**

Source: verified original v6.32.91 ZIP (49 files). Original code changes: `.dockerignore` and `README.md` documentation only. All processing code, authentication, UI and Excel-export modules are byte-for-byte unchanged. New packaging/configuration/docs files are included below.

## Included files

```text
.dockerignore
.env.example
.gitignore
CROSSMATCH_DOCKER_CONTROL.ps1
Dockerfile
GENERATE_SETUP_KEY.bat
GENERATE_SETUP_KEY.ps1
OPEN_APP.bat
README.md
RESET_ADMIN.bat
START_DOCKER.bat
STOP_DOCKER.bat
app.py
config.py
deploy/linux/preflight.sh
docker-compose.server.yml
docker-compose.yml
docs/GITHUB_UPLOAD_AND_SERVER_DEPLOYMENT.md
docs/SECURITY_AND_ROLLBACK.md
engine/__init__.py
engine/crossmatch_engine.py
engine/csv_workbook.py
engine/exhaustive.py
nginx/40-crossmatch-certificate.sh
nginx/Dockerfile
nginx/default.conf
requirements.txt
reset_admin.py
services/__init__.py
services/advanced_conditions.py
services/auth_manager.py
services/csv_export.py
services/desktop_export_style.py
services/duplicate_group_styles.py
services/excel_export.py
services/fast_excel.py
services/field_profile.py
services/header_detector.py
services/job_manager.py
services/sequential.py
services/session_manager.py
services/value_suggestions.py
services/worker.py
static/css/app.css
static/js/account.js
static/js/admin.js
static/js/app.js
static/js/auth.js
static/js/register.js
templates/account.html
templates/admin.html
templates/index.html
templates/login.html
templates/register.html
templates/setup.html
docs/FILE_MANIFEST.md
```

## Excluded from GitHub

Actual `.env`, `database/`, `certificates/` (especially private keys), `cache/`, `uploads/`, `results/`, `exports/`, backups, logs, any beneficiary Excel/CSV, temporary files, personal tokens, and pre-existing production ZIPs.

Review staged files before every push. `.gitignore` cannot remove sensitive material already committed to repository history.
