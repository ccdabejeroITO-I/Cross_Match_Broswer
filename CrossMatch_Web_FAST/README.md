# GitHub-ready source package — CrossMatch Browser v6.32.91

**Start here for deployment:** [GitHub upload and Windows Server guide](docs/GITHUB_UPLOAD_AND_SERVER_DEPLOYMENT.md) · [Security and rollback checklist](docs/SECURITY_AND_ROLLBACK.md).

Use `docker-compose.yml` for the existing Windows 11 development environment. Use the separate `docker-compose.server.yml` only on an approved Linux VM with Docker Engine behind the Windows Server host. **Docker Desktop is not supported on Windows Server.** This packaging does not change matching, rule evaluation or Excel export behavior. Never commit private `.env`, the `database/`, `certificates/`, cache, beneficiary files or results.

---

## v6.32.91 — Four rule actions, stage-safe templates, and no visible Excel group-heading rows (2026-10-29)

- Unhid the existing validated/duplicate backend rule actions, with explicit eligibility warnings. A rule cannot create an identity match, override strict DOB Review, or reclassify an accepted duplicate as Clean.
- Template insertion uses actual File A headers, avoids duplicates in the active stage, and names missing header mappings. Rules remain disabled until reviewed.
- Stage switching updates the active Process 1/2 condition view without auto-saving rules; separate rule arrays remain intact.
- The Sequential CSV retains verified group boundaries for conversion, but the generated XLSX no longer displays numbered `GROUP N` heading rows. Process section headings, actual group colors, File B reference-first and original public column schema remain unchanged.
- No matching thresholds, identity scoring, account database schema, or Docker volumes are changed. Test with a backup of the current app and existing `.env`/`database`/`certificates` preserved.

## v6.32.90 — Shared Condition Builder modal (2026-10-29)

The Header Mapping `+ Add condition` and `Edit condition` buttons now use the existing **Conditions & Rule Builder** modal rather than a separate, mapping-only form. When opened from Header Mapping, Save Changes atomically persists the selected mappings and rules using the existing session editor-config API; Cancel returns to the mapping draft without saving. Existing text/numeric/date operators plus 5 verified additional operators (Starts With, Ends With, Does Not Contain, Greater Than or Equal, Less Than or Equal), versioned backward-compatible rule metadata, stage handling, AND/OR, condition previews, saved profiles, strict DOB validation, name matching, Keep One default ON, four-sheet Excel, and authentication remain in place. No database migration.

**Data safety:** Preserve `database/`, `certificates/`, `.env`, uploads, Docker volumes, and user configurations. Backup before upgrading, stop active jobs, extract over the source folder, run `START_DOCKER.bat`, and check `/api/health` for `6.32.90`. Do not run `docker compose down -v`.

**Limitations:** This update uses the existing single-level AND/OR grouping. It does not add arbitrary nested boolean groups, two-File-A-field comparisons, general Between operators, N-day relative date operators, or automatic semantic-field migrations for profiles. Operator choices shown in the UI have evaluator support, and new configurations use rule schema version 2 while legacy profiles remain readable. Test with de-identified inputs before production.

## v6.32.89 — Process 1 duplicate rows only (2026-10-29)

**Correction:** In File A self-deduplication, the `DUPLICATE RECORDS` worksheet now contains ONLY rows classified as duplicates. A verified exact-subgroup representative retained in Process 1 Clean remains in `VALIDATED RECORDS` (or proceeds to Process 2 in Sequential mode); it is no longer inserted a second time as `REFERENCE (FILE A - CLEAN)`. Every actual File A duplicate row retains its real DedupType and MatchPercentage instead of being relabeled `REFERENCE` merely because it is the first row of a group. Source-row match evidence remains in ConflictReason. Process 2 still displays actual File B reference rows first.

**No change to:** exact/fuzzy/swapped detection, strict DOB Review classification, Keep One defaults (ON for new configurations, explicit OFF preserved), Rule Builder, header mapping, login, user permissions, Docker persistence, or approved four-sheet workbook schema. Version 6.32.89 requires normal Docker image rebuild through `START_DOCKER.bat`; preserve all private volumes and settings. Test on de-identified inputs before production use; local Windows Docker not exercised here.

## v6.32.88 — Unified DSWD Condition Builder (2026-10-29)

**Changes relative to v6.32.87:** Added a beginner-facing **Simple Mode** and a reversible **Advanced Mode** to the existing Rule Builder, selectable Process 1/Process 2 stage per rule, and a safe `Both processes — File A validation only` choice in Sequential mode. Shared A-only checks are included in Process 2 as A-only rules (not converted to File A vs File B comparisons). Direct Cross Match supports both File A-only validation and A↔B paired-field checks. Existing advanced AND/OR grouping and numeric/date/text operators remain the authoritative condition engine; no separate evaluator was added.

Six **optional, disabled-by-default** DSWD program example templates use only actual uploaded headers (General Beneficiary, AICS, Social Pension, UPLIFT/G2P, Fuel Subsidy, 4Ps/Household). These are **not official eligibility rules**. A bounded, authenticated `/api/condition-rule-preview` endpoint uses the existing condition-evaluation functions against at most 100 File A source rows, or against expressly entered illustrative A/B values; the latter are **not claimed to be accepted identity matches**. The preview never writes classifications or beneficiary data to account storage. A timeout restores the Test button. The saved account-level profiles now support both processing stages in one profile; old single-stage profiles remain compatible. Rule IDs and stage metadata are retained for future save/reload operations.

**Unchanged:** Matching thresholds/algorithms (`engine/crossmatch_engine.py`), name/DOB validation, File A-only classifications, File B reference-only handling, Keep One TRUE_DUPLICATE ON by default (Process 1 only), sequential workflow, four-sheet Excel export, account system, Docker volumes and persistent settings. No persistent database migration was made. The `/api/health` application version is `6.32.88`; the matching-engine version remains `NameCoreFuzzy-6.32.87-keepone-default-on` because matching code was not modified.

**Known limits:** Existing AND/OR groups are flat; arbitrarily nested logical groups were not added. Additional unsupported operators are deliberately not exposed. Cross-file Test Rule uses user-provided example values, rather than attempting to pair unrelated upload rows. Representative production datasets and the user's actual Windows Docker environment were not tested here; validate against controlled synthetic/sample files before real beneficiary processing.

**Update safely:** Back up the v6.32.87 project and all persistent data, finish active jobs, copy updated application files into the **same original installation folder** without overwriting `.env`, `database`, `certificates` or uploads, then run `START_DOCKER.bat`. Check `/api/health` for `6.32.88` and refresh the browser using Ctrl+F5. Roll back by restoring previous application code while retaining volumes and persistent data. Never use `docker compose down -v` or prune volumes.

---

## v6.32.88 — Keep One TRUE_DUPLICATE ON by default (2026-10-28)

**Default change:** For new settings and requests without an explicit Keep One value, the checkbox and backend now default to ON **for Within File A / Sequential Process 1 only**. Any explicit OFF choice saved starting with this release remains OFF across browser refreshes and new sessions using this signed-in user's browser preference. The setting also travels with a saved Header Mapping session configuration; older session configs missing the field inherit ON. Earlier releases never persisted an explicit Keep One preference, so historical intentional OFF choices cannot be reconstructed automatically. Direct File A vs File B and Sequential Process 2 never run Keep One, regardless of the checkbox state.

Representative selection itself is unchanged from v6.32.86: after mandatory validation it retains one eligible member per actual `(duplicate group, verified normalized final_key)` TRUE_DUPLICATE subgroup with at least two eligible members; it never promotes singletons simply because they display TRUE_DUPLICATE or 100%. Exact middle-name behavior continues to follow the explicitly selected mapping. File B remains reference-only and is not counted. Stage logs report only aggregate counts and effective settings, without beneficiary names or birthdays.

**Safety:** Complete application files only; preserve `.env`, `database/`, `certificates/`, uploads, saved results and Docker volumes. Finish active jobs, back up existing files, install into the original directory, then run `START_DOCKER.bat`. Validate `/api/health` for version 6.32.88 after Docker rebuild. This release was not tested against the 13,350-row production workbook or your running Windows Docker image.

## v6.32.86 — Keep One TRUE_DUPLICATE eligibility and Middle Name mapping fix

The **Keep One TRUE_DUPLICATE Record in Clean** option remains **OFF by default**, and applies to **Process 1 File A self-deduplication only**. When enabled, the engine retains exactly one eligible representative per verified `(duplicate group, full exact identity key)` subgroup with at least two confirmed TRUE_DUPLICATE members, after mandatory DOB/name Review validation. A single TRUE_DUPLICATE-classified row in a broader fuzzy family is **not** enough to qualify; it stays in its existing classification pending legitimate evidence. No File B-to-File B deduplication is performed, and Process 2 never applies Keep One.

The Web backend now preserves explicitly selected **Middle Name and Suffix** Find Duplicates checkboxes while repairing header mappings. Previously, the mapping repair forced these options ON despite being unchecked. Historical legacy mapping files without the `explicit_mapping` marker keep their previous fallback behavior. The exporter reads a dedicated per-row retained-representative marker instead of inferring which Clean rows were selected; retained references are displayed only as supporting evidence. Processing logs report subgroup counts without beneficiary names or birthdates.

Back up the original installation and persistent data, finish current jobs, replace application files in the **original folder**, and retain `.env`, `database/`, `certificates/`, uploaded files and Docker volumes. Verify `/api/health` returns `6.32.86` after the safe Docker upgrade. The supplied synthetic tests do not verify any particular real-world Group 76 without its source workbook and original mapping selections.

# CrossMatch Browser v6.32.86 — Default Indexed Fuzzy Processing

The earlier v6.32.81 performance update was based on v6.32.80 and added two new
SQLite expression indexes for the existing compact-name and compact-phonetic
rescue joins. The input expressions, matching rules, threshold, candidate
coverage, and order of fuzzy scoring have not changed. Added web-only CPU
reservation and best-effort lower scheduler priority for the matching child
process, which may trade maximum standalone scoring throughput for browser
responsiveness. Default: reserve one CPU in Docker when >=2 are available;
`CROSSMATCH_RESERVE_WEB_CPU=0` opts out. `CROSSMATCH_BACKGROUND_NICE=0`
opts out of lower Linux scheduler priority. These changes do NOT eliminate
89 million unique candidate pairs and are NOT proof of an overall speedup.

Do not overwrite your original database, certificates, or .env. Backup existing
installations before copying files into the same original project directory.
Use the safe Docker upgrade flow. Never use `docker compose down -v` or prune
volumes. Always verify the current engine build in `/api/health`.

# CrossMatch Browser v6.32.80 — File A Only Outcomes / File B Reference Audit

Based on v6.32.79. Added a streaming, fail-closed pre-export classification integrity check of all File A rows and File B reference row identifiers. No changes to candidate generation, RapidFuzz scoring, or matching thresholds. Sequential exports include reference-only counts in job metadata. File B is never classified independently. Existing Docker scripts, UI and persistent data paths are preserved.

**Performance limitation:** 89M unique candidate-pair bottleneck is not resolved in this release. Desktop v6.33 classification is not equivalent to current Web scoring; no unsafe engine replacement was made. Actual Windows Docker and production data tests were not possible in the test environment.

# CrossMatch Browser v6.32.80 — Fuzzy Scoring Fast Path + Build Fingerprint

Based on the complete v6.32.77 project. The app/UI, Docker controls, header mapping, three modes, rules, authentication, sequential worker, and four-sheet export remain unchanged except for version/fingerprint display in diagnostics.

**Targeted performance update:** 7 bounded, per-process cached deterministic name helper functions; avoid redundant RapidFuzz QRatio calls (equivalent to ratio for non-empty inputs), redundant token-sort calls for single-token components, and duplicate compact scoring when input has no whitespace. The original scoring formulas, similarity thresholds, candidate lanes, SQLite unique-pair deduplication, DOB rules, and classifications remain intact. Worker log now records active engine source fingerprint and processing configuration; `/api/health` and `/api/selftest` expose a build fingerprint from the source loaded at startup. Caches reset at the start of each scoring stream. No arbitrary pair cap or filtered-out candidates were added.

**Measured local scorer-only benchmark (synthetic 19,000 pairs; 14,000 repeated-name-pattern + 5,000 high-cardinality):** prior v6.32.77 4.47s, updated 2.24s on first identical-input run (~2.0× speedup), with identical SHA256 of every score result. These are NOT production processing times and do not demonstrate reduced 89M candidate pairs. Within File A/Cross and Sequential sample matching integrity must be confirmed before use on real beneficiary data. CPU contention, data distribution, Docker CPU limits, and cache hit rates affect actual performance.

**Deployment:** Complete jobs first; backup original project including the `database`, `.env`, `certificates`, uploads, results and Docker volumes. Extract this ZIP, copy application files into the existing project directory, preserving all user data/private config. Run `START_DOCKER.bat` and confirm `UPDATE` only when no active jobs are running. Verify `/api/health` returns version 6.32.80 and `engine_build`, then compare representative saved test results before production. If startup/regression fails, stop safely and restore the v6.32.77 application code, leaving data volumes unchanged. The user’s live Windows Docker engine cannot be interrogated from this test environment.

---

# CrossMatch Browser v6.32.77 — Indexed DOB Candidate Discovery Optimization

**Based on the complete v6.32.76 project**, preserving the account system, three Comparison Modes, header-mapping popups, sequential worker, four-sheet export, and guarded Windows Docker upgrade launcher.

- Replaced one large `birth=birth AND (last-name-anchor OR first-name-anchor)` fuzzy candidate-discovery JOIN with **two separate indexed DOB+name JOINs**, using the existing `(birth,last_name)` and `(birth,first_name)` indexes. The two passes are set-equivalent to the previous OR predicate. The `INSERT OR IGNORE` primary key prevents duplicate scoring without dropping qualifying candidates. Fuzzy name/DOB scoring and grouping code remains unchanged.
- Records per DOB lane, elapsed time and unique additions are logged separately.
- Avoids two full-table `COUNT(*)` queries on the SQLite candidate table when weak-rescue processing is disabled; this leaves all candidates unchanged.
- Retains *every* existing fuzzy lane, exact/swap scoring, original thresholds, uncapped candidates, DOB validation, Review precedence, and full File A record integrity. No unverified pruning, birth-year exclusion, or additional cap.

**Measured:** Synthetic 20,000 A × 20,000 B rows, the affected DOB-assisted SQL pass 1.225s → 0.143s (8.57×, 97,086 identical pairs). The smaller 7,000×7,000 case 0.134s → 0.019s (7.22×, 8,920 identical pairs). **These are isolated join microbenchmarks, not total application runtimes or representative 89-million-pair results**. End-to-end 171×126 sample produced exactly identical record-level results in Within, Cross, and Sequential modes; timings were effectively unchanged. The 89M genuinely unique candidate issue is **not yet demonstrated solved**; no speedup is claimed for that production workload. See the accompanying performance report.

**Deploy:** Backup existing `database/`, `.env`, `certificates/` and account data; copy this release's application code into the *same original CrossMatch project folder*, not a new folder with empty volumes. Wait for active jobs to finish. Use `START_DOCKER.bat`, follow its explicit `UPDATE` confirmation if a prior version is running, and verify `6.32.77` and `/api/health` on port 18090. No GitHub changes were made. Actual Windows Docker Desktop, live government data and 500K–1M-row workloads were not tested.

---

# CrossMatch Browser v6.32.76 — Safe Docker Existing-Container Verification Fix

Fixes the startup diagnostic `Cannot confirm where the existing CrossMatch container was created` when the Docker Compose `project.working_dir` label cannot be read by PowerShell 5.1. The launcher now reads structured `docker inspect` JSON and verifies the **actual persistent bind-mount source** of both `/app/database` (web) and `/etc/nginx/certs` (proxy) against the current installation's `database` and `certificates` folders. It confirms the Compose project and service identity. The label is treated as supplementary information rather than the only way to validate the original folder.

**Safety:** The launcher still refuses to alter existing containers if bind mounts point to a different directory or cannot be safely identified, and the explicit `UPDATE` confirmation and active-job checks remain in place. `STOP_DOCKER.bat` also verifies project and persistent data paths. No Docker prune, `down -v`, account migration, or automatic deletion is introduced.

**Upgrade:** Back up the original installation, including `database`, `.env`, and `certificates`. Copy **application files** from this ZIP into the same directory that owns the existing running container's `database` mount. Do not run this release from a newly extracted folder with a different `database` directory. Run `START_DOCKER.bat`, check that no jobs are active, and enter `UPDATE` if upgrading an older running container. The complete ZIP contains no private database or .env files.

**Compatibility:** No deduplication, matching, mapping, or export logic has changed from v6.32.75; only Docker control and version strings changed. Windows 11 Docker Desktop runtime testing must be completed on the target PC; local build tests are static and simulated unless explicitly stated.

---

# CrossMatch Browser v6.32.75 — Inline Manual Header Mapping

Adds transactional + Add Header inside Edit Name and Edit DOB mapping popups, Save Changes/Cancel, searchable File A header lookup and File B pairing. All previously working functionality and v6.32.74 Docker upgrade checks remain.

# CrossMatch Browser v6.32.74 — Safe Upgrade from Running Older Docker Containers

**Fix:** When `START_DOCKER.bat` encounters an older running CrossMatch container (for example, 6.32.71), it no longer stops with a generic version mismatch. The PowerShell helper checks saved job statuses; if it detects active jobs or cannot check them, it does not stop anything. If no jobs are active, the user can explicitly type `UPDATE` in the START command window to stop only this CrossMatch Compose project, rebuild/recreate its containers from the copied v6.32.74 source, wait for health, and verify the expected running version.

**No deletion:** Uses `docker compose stop` and `docker compose up -d --build --force-recreate`; never uses `down -v`, prunes volumes, clears data, or stops unrelated Docker projects. Existing bind-mounted `database/`, `.env`, `certificates/`, and the named cache volume remain outside the image. Current active jobs must finish **before** selecting the upgrade option.

**Procedure:** Back up your folder and data, finish processing, copy the updated project files into your existing CrossMatch folder without replacing private data, and run `START_DOCKER.bat`. If an older version is running, review the message and type `UPDATE`. If the app is already on 6.32.74, startup will not recreate it unnecessarily. `STOP_DOCKER.bat` is unchanged.

**Compatibility:** Windows PowerShell 5.1 on Windows 11, Docker Desktop Linux Containers, HTTP port 18090. Do not run these scripts from an automated, noninteractive shell; the approval prompt is intentional.

**Testing limitation:** The ZIP, Python and JavaScript syntax can be tested on Linux, but the Windows Docker Desktop interaction and live upgrade still need validation on the user's Windows machine. The production deduplication engine and Excel export are unchanged.

---

# CrossMatch Browser v6.32.73 — DOB Headers and Fuzzy Scoring Efficiency

Preserves all existing v6.32.72 Docker fixes and Web application features. Updated header alias/context detection and fuzzy-scoring cache lifetime with container-aware worker scheduling. No candidate cap was added; record classifications are unchanged by the performance changes. See the included release report for measured tests and limits.

---

# CrossMatch Browser v6.32.72 — Windows Docker Startup/Stop Safety Fix

**Updates only Docker control scripts, one new PowerShell helper, and version tags.** All CrossMatch business logic, Rule Builder, sequential, account, dataset and export code remains unchanged.

Run `START_DOCKER.bat` or `STOP_DOCKER.bat` on Windows 11 (Docker Desktop, Linux Containers). The PowerShell helper uses built-in Windows PowerShell 5.1 and the existing Compose configuration; no host Python is necessary.

Startup distinguishes: missing Docker CLI, missing Docker Desktop, engine not ready, wrong Windows Containers mode, missing Compose, active TCP port conflicts, unhealthy app, and version mismatches. When installed but closed, it attempts to launch the verified Docker Desktop.exe and waits up to `CROSSMATCH_DOCKER_START_TIMEOUT` seconds (default 120, allowed 15–900). It never changes Docker context, container mode, WSL settings or installs software. `CROSSMATCH_HEALTH_TIMEOUT` (default 180, allowed 15–900) controls the app health wait. Both values may be specified via `.env` or the Windows process environment.

Startup verifies web and proxy container health, `api/health`, `api/selftest`, and running version **before** reporting READY. Already-healthy containers are not force-recreated. If a different version is already running, the script does not interrupt it; manually stop active processing and stop/restart when safe. The first-admin key generator runs only when the existing database file is absent.

Shutdown checks engine reachability before `docker compose stop`; if the engine is down, it explicitly reports that the state cannot be verified. It never launches Docker Desktop merely to stop CrossMatch, never deletes data or volumes, and never terminates other apps.

**Installation:** Back up `database/`, `certificates/`, `.env`, and relevant volumes; extract/copy new application files but retain private deployment data and any deliberate `docker-compose.yml` customization. For upgrades with an existing v6.32.71 container, finish jobs and stop it while Docker Desktop is running before installing updated application files. Run `START_DOCKER.bat` and check the reported version and health before processing sensitive data. Host-specific Windows/Docker tests must be completed on the target laptop; this release's Linux environment cannot start Docker Desktop or verify Win11 runtime behavior.

---

# CrossMatch Browser v6.32.71 — Comparison Mode and Worksheet Update

This update continues from the user's v6.32.70 Web ZIP. The matching engine,
existing account management, upload and Excel export APIs are retained.

- Processing mode is held centrally in `state.comparisonMode`. The Comparison
  Settings dialog, File A/B upload visibility, header mapping, Rule Builder,
  processing request and backend worker use that selection.
- File A Only never submits or processes File B. Cross Match requires both.
- **New Sequential mode:** Stage 1 within-file dedup, then Stage 2 crosses only
  Stage 1 Validated/Clean File A rows against File B. Stage 1 Duplicate/Review
  rows remain in the final categories. Independent conditions for the two
  stages are selected in the Rule Builder. Final results are a four-sheet
  workbook or CSV ZIP with A-row count integrity verification.
- Independent Excel worksheet selectors follow the corresponding uploaded file;
  CSV inputs do not display worksheet selectors. Switching a worksheet only
  invalidates rules referencing headers that no longer exist.
- Corrected front-end/server version discrepancy and startup version check.
- CSV-to-Excel duplicate-group shading now reads the existing `DedupType` column.

**Limitations:** Sequential uses the existing Web matching algorithm twice,
not the older desktop's separate Keep-One-TRUE_DUPLICATE-in-Clean policy.
It produces XLSX via the Web's existing CSV-to-Excel converter, so the
advanced native-engine Excel styling may differ. 500k–1m-row workloads,
Windows Docker deployment, user registration, and admin flows have not been
validated for this release. Validate beneficiary decisions on a copied sample
before production. Backup `database`, `certificates` and `.env` before upgrade.

---

# CrossMatch Web v6.32.70 — Selective v6.33 Multi-pass Integration

This build continues from the verified v6.32.69 Web source. It does **not**
replace the Web engine with the desktop GUI engine.

- Integrated safe, conservative month/day/year normalizers from the desktop
  v6.33 approach, including aliases, `.0`/`.00` cleanup in matching keys,
  rejection of fractional years and no automatic two-digit-century guesses.
- Kept the Web-specific column-level MDY/DMY date-order inference and
  20-lane fuzzy candidate discovery and scoring architecture.
- Added indexed exact-DOB + dual-name-edge candidate passes (normal/reversed)
  from the v6.33 recall strategy. These passes discover candidates; they do not
  independently confirm identity.
- Independently validates required names, optional populated middle/suffix and
  complete DOB. Suspicious original source strings remain intact in exports.
- Records with mandatory invalid/missing identity evidence finish in Review,
  even when an identity candidate is detected; type and similarity are retained
  as audit evidence in the Review workbook row.
- Detailed invalid day/month/year explanations appear in ConflictReason.
- Final exported XLSX tabs: SUMMARY, VALIDATED RECORDS, DUPLICATE RECORDS,
  RECORDS FOR REVIEW. The three computed visible columns are DedupType,
  MatchPercentage and ConflictReason; Cross Match can also expose original
  File B-only headers needed to display reference records.

**Scope and limitations:** the older Web v6.32.69 archive does not contain a
sequential self-dedup + cross-match macro. This release does not add that
separate desktop workflow or change its Keep One TRUE_DUPLICATE in Clean
behavior. The Web advanced Rule Builder, sessions, UI, accounts and Docker
configuration are preserved in source, but browser, authentication and real
Docker deployment tests have not been run for this integration. There is no
verified 500K–1M-row performance benchmark for this release. Before handling
production beneficiary data, back up your application/database, use a copied
sample to validate expected classification changes, and review the generated
RECORDS FOR REVIEW category.

To run the synthetic regression suite from the external audit package, use:
`python -m unittest discover -s tests -p test_v633_integration.py -v`.

---

# CrossMatch Browser 6.32.69

> Secure first-install bootstrap release. Existing accounts and ordinary administrator-approved registration are preserved.

> Regression-tested maintenance release: stricter invalid CSV-header validation, date-condition parsing for Excel datetime values, and a private-data-free distribution. Name/DOB row editors, matching modes, account approvals, and exports are preserved. See the separate hard-test report for workload coverage and limits.


## Search uploaded headers inside Smart Autocomplete (v6.32.69)
- When the **Value or text to match exactly** input is focused, the suggestion panel now offers **Cell values** and **Search headers**.
- Search headers by name (for example `first name` also matches `first_name`) without loading any extra cell data.
- Selecting a header updates **Which field should be checked?** (or **File A field to check** in Cross Match). Cross Match automatically re-suggests the File B counterpart.
- Selecting a header clears the previous exact-value text to avoid accidentally using it against the wrong column; then actual suggestions from the new column appear.
- The header name is never inserted into the exact-value text field. Existing matching logic and rules are unchanged.
- START_DOCKER.bat now checks the correct installed application version.

## Cross Match mode-aligned conditions and smart paired headers (v6.32.68)

- Cross Match creates File A ↔ File B comparison conditions from the Rule Builder **and** Header Mapping actions. Within File A creates File A-only rules.
- File B condition headers are auto-suggested only for confident header/meaning matches; manual selection stays available. Changing File A header updates its proposed pair.
- Legacy single-file rules accidentally stored in Cross Match are converted but **disabled pending review**; older saved setups are retained.
- Smart exact-value autocomplete also works for the optional File A equals-value filter in a cross comparison.
- Mode checks are enforced before submission.

## Smart Autocomplete search fix (v6.32.67)

The exact-value Rule Builder input now opens real examples from the selected uploaded column on focus; typing a query returns up to 10 actual values, first prioritizing values that start with the query, then values containing it anywhere (case-insensitively). When no match exists, the dropdown identifies File A/B, selected column and number of indexed distinct nonblank values to help spot wrong-column selections. Entries typed manually remain allowed. The first query builds an upload/session-scoped index, reusing it for later queries. This release does not auto-suggest column headers as cell values. No matching or export logic was changed.

## Smart rule operator and input upgrade (v6.32.66)

Selecting an uploaded File A / File B column now recommends **text, numeric or date** checks using a bounded sample of actual uploaded cell values (or the header as a fallback). The operator dropdown shows the most relevant supported checks first, with a **Show all check types** override. Saved operators are preserved; type hints never silently alter existing rule logic. IDs and leading-zero codes are treated as text.

New fixed **On selected date** and **Not on selected date** checks use a date picker and real calendar-date comparisons, while **Equals number** and **Does not equal number** use numeric comparisons (without matching empty/non-numeric cells). The old exact-text operators and autocomplete still work. Date, numeric, text, and no-value entry widgets change with the selected operator. No changes to cross-file comparison behavior.

## Exact-value autocomplete (v6.32.65)

The Rule Builder's **Value or text to match exactly** field now suggests up to 10 distinct existing values from the selected File A/File B column. Type two or more characters. Mouse selection, Arrow Up/Down, Enter and Escape are supported. Manual text is always allowed.

For large CSV/XLSX uploads, the first lookup for each selected column builds a temporary, disk-backed index once. Later keystrokes perform fast prefix lookups. Suggestions are private to the current user's session and selected worksheet. If the suggestion index cannot be built, manual input remains usable. Indexed values are cleaned up with the temporary CrossMatch session; the matching engine and saved rule format are unchanged.

## One-time first administrator key (v6.32.66)

**First-time Windows setup (`START_DOCKER.bat`)**

1. On a fresh installation, `START_DOCKER.bat` calls `GENERATE_SETUP_KEY.bat`, which uses Windows PowerShell's cryptographic random-number generator to generate a **64-character hexadecimal key** and save it to the local `.env` file as `CROSSMATCH_SETUP_KEY`. The key is also displayed in the server's Windows console. It never appears in the public app HTML or API.
2. The first administrator opens `/setup`, enters their username, display name, password (at least 10 characters), and the **one-time setup key**. Submit **Create administrator**.
3. The app creates the admin account and atomically marks first-time setup complete in the SQLite database. The setup key **cannot be reused**, even if someone later deletes the last user row while retaining the database. The password and key are distinct.
4. Subsequent users select **Create account** on the sign-in page and stay **Pending Approval** until an administrator approves them. They cannot sign in before approval.

**Server setup and protection**

- Keep `.env` private; do not upload, commit, or email it. Keep the first-admin key confidential and access setup over HTTPS when using a remote browser. After creating the first administrator, you may remove the `CROSSMATCH_SETUP_KEY` line from `.env` and restart the Docker stack; existing accounts are unaffected. Do not remove other `.env` settings.
- If you start Docker Compose directly (without `START_DOCKER.bat`), **first** run `GENERATE_SETUP_KEY.bat` on your Windows server, or provide your own cryptographically random `CROSSMATCH_SETUP_KEY` of 32–256 ASCII letters/numbers, `_` or `-` through the server environment or `.env` file. The server **refuses first-admin creation** when the key is absent or invalid.
- `GENERATE_SETUP_KEY.bat` preserves an existing valid key and existing `.env` values; it does not rotate or overwrite an existing key. For an unusual state where a database file already exists but has no accounts, run the generator manually if necessary.
- The API enforces the key server-side, checks it using constant-time comparison, and limits invalid attempts to 8 within 15 minutes per client IP. The setup is one-time and an attempted second bootstrap is rejected, even with the correct key.
- **Upgrades:** keep your existing `database`, `certificates`, `.env`, and Compose customizations. Existing administrators log in normally; they do not need to regenerate a key. Existing SQLite authentication records and prior-approved users are preserved.
- If the account database was initialized then all user records were deleted, first-time setup remains blocked; restore an account database backup or use appropriate local recovery. Deleting the database to reactivate setup risks losing accounts and audit history and is **not** recommended.
- `.env` is never included in this distribution ZIP or Docker image. The Windows key generator is not run or tested in this Linux test environment; it should be verified on a Windows machine before production use.

## Account page usability update (v6.32.63)

- Sign-in page uses a clear **Create account** action with separate notice that administrator approval is required.
- Registration shows three stages: enter details, administrator review, and sign in after approval.
- Password fields have accessible show/hide controls, inline password confirmation feedback, and useful field hints.
- The success screen explains that the request was received, does not guarantee approval, and tells the applicant to contact an administrator for status.
- The existing registration endpoint, duplicate-request privacy behavior, administrator queue, login permissions and database are unchanged.

## Hard-tested maintenance fixes (v6.32.62)

- **Malformed CSV replacement:** reject files whose detected column headers are empty or contain binary/control characters; keep the previously accepted upload when the replacement is invalid.
- **Advanced date conditions:** evaluate Excel-staged datetime text (e.g. `2025-01-20 00:00:00`) as a valid calendar date, including common datetime timestamp formats in CSV.
- **Release hygiene:** this ZIP does **not** contain any previously deployed SQLite authentication database or TLS key/certificate. On a new install, the first admin can be created as usual, and the nginx certificate helper generates a local certificate. On an upgrade, preserve your existing database, certificates and any local `.env`.

The hard-test evidence includes 500,000-record and 1,000,000-record synthetic CSV runs, 1,000,000-record Excel workbook conversion, smaller fuzzy/swap and cross-file runs, varied condition cases, and browser control tests. Testing is not a guarantee for all input variants or hardware.

## Start

Install Docker Desktop, select Linux containers, and start Docker Desktop.
Extract this ZIP into a folder, then run **START_DOCKER.bat**. The first build
needs internet access. No Python installation is required on Windows.
Create the first administrator account with the one-time server setup key when the browser opens.

Default addresses: http://127.0.0.1:18090 and https://localhost:18444.
HTTPS uses a locally generated certificate. Configure ports and settings using
`.env.example` as the template for an optional `.env` file.

## Included helpers

- START_DOCKER.bat: build, start, verify the version, and open the app.
- OPEN_APP.bat: reopen an already running app.
- STOP_DOCKER.bat: stop the app without deleting its stored accounts.
- RESET_ADMIN.bat: recover an existing administrator account using Docker.

Diagnostics: run `docker compose logs --tail 100` in this folder.
Status: run `docker compose ps`.

## Upgrade safely

Keep your existing `database`, `certificates`, `.env`, and any customized
Compose settings. Replace application files and run START_DOCKER.bat to rebuild.
The registration-request tables are automatically added to the existing SQLite database. Do not delete existing data folders just
because they are not included in this clean distribution.

## Account registration and admin approval

After the first administrator has been created, the **Sign in** page has a
**Create account** link. Applicants enter a username,
full name and password. Submission creates only a pending request; it does not
create an active user or permit sign-in. The password is stored as a salted
scrypt hash, never in plaintext. An administrator opens **Administration →
Pending account approvals**, verifies the applicant, and chooses **Approve**
(to create a standard-user account) or **Reject**. The applicant can sign in
with the submitted password only after approval. This workflow does not send
emails or automatic approval notifications.

Direct administrator-created accounts continue to work without requests.
Registration requests and decisions are retained in the existing local SQLite
database and audit trail. The new tables are created automatically on startup
in the existing database; do not delete or replace the `database` directory.
The public request form has rate limits but does not include CAPTCHA, so avoid
exposing this app to an untrusted public network without additional protection.

## Row-specific header editing (v6.32.61)

Under **Unified Header Mapping & Rules**, select **Edit** on the **Name** row to
edit only detected Name headers (Full Name, First, Middle, Last, Suffix) or
**Edit** on the **DOB** row to edit only DOB headers (Full Birthdate, Birth
Month/Day/Year). Only headers detected and assigned to that group appear.
The top-level **Edit headers** button still shows all columns for reviewing
uncertain or incorrectly classified headers.

Inside the mapping pop-up, **+ Add condition** beside a header creates a new
condition for that specific column, then opens the existing **Rule Builder**
so you can choose the operator, value and result. In Cross Match mode it
prefills the corresponding File B comparison where available. A rule is not
completed until its remaining settings are configured. These are *optional*
advanced checks; they do not modify default Name/DOB duplicate identity
matching. Existing rule profiles are not overwritten automatically.

## Conditions

Upload File A, review detected headers, and open Rules & saved setups.
Enable Conditions and add text, numeric, date, or missing-value checks.
Cross Match also supports File B checks and comparisons on accepted A/B pairs.

Rules in the same group run in priority order. Each rule's AND/OR selection
combines it with the previous result in that group. The first rule's selection
has no effect. Separate groups trigger independently. File B-only checks must
use a separate group from File A and A/B checks; invalid mixed groups now show
an error instead of silently evaluating incomplete groups.

Accepted duplicate matches remain Duplicate even when a rule adds a Review
finding. The exported Reason records that finding. A Duplicate action cannot
create an identity match by itself. Review findings override Clean requests.

Saving with Conditions OFF preserves individual Enabled selections. Profiles
already saved by older versions with all rules disabled need those selections
restored manually once.

## Age limits

Minimum and maximum age default to **0 (OFF)**. A positive value enables that
bound. Valid out-of-range DOBs generate Review findings. Full DOB and separate
month/day/year mappings are supported. Existing duplicate precedence remains.

## This clean distribution

Contains runtime code, Docker configuration, four useful Windows helpers,
admin recovery, and this guide. Historical notes, duplicate guides, test and
benchmark folders, test dependencies, caches, and redundant diagnostic/test
batch files are excluded. No test accounts, uploaded data, populated database, or TLS private keys/certificates are included.


## v6.32.80 — startup readiness and diagnostics (2026-10-27)

- Local HTTP `127.0.0.1:18090` readiness checks the **web** container health
  and verifies the versioned `/api/health` and `/api/selftest` endpoints.
- The optional HTTPS `proxy` container (port 18444) now has a separate status.
  A proxy-only failure is reported as a warning when the local HTTP Web app is healthy.
- Startup prints container states/restarts, recent Docker healthcheck output,
  HTTP endpoint diagnostics, and web/proxy logs when the HTTP app fails to start.
- `docker compose up -d` starts services without a second Compose `--wait`
  readiness gate. The launcher still performs its own health polling and
  **never reports READY for an unhealthy Web backend**.
- The existing confirmed `UPDATE` prompt, active-job safeguards, project
  identity/bind-mount verification, and database/volume protection remain.
- No change to matching algorithms, classification rules or Excel exports.

If Web still does not start on your Windows 11 machine, run these commands
in PowerShell **inside the original CrossMatch project folder**, then inspect
or share the results after removing any sensitive information:

```powershell
docker compose ps -a
docker compose logs --tail 80 web
docker compose logs --tail 50 proxy
```

These commands only inspect status and logs; they do not remove data.


### v6.32.82 default matching profile
The previous default `Comprehensive + Maximum recall (Exhaustive)` option caused all-pairs quadratic fuzzy scoring. The Web workspace now always uses the existing indexed multi-pass candidate engine when Fuzzy matching is enabled. Turning Fuzzy off intentionally runs exact-only mode. The backend rejects stale API requests that explicitly ask for exhaustive mode, to avoid silently changing the requested recall contract; use Ctrl+F5 to refresh. The CLI/internal exhaustive module remains unmodified for regression comparison; it is not exposed in the Web interface. Indexed blocking is not mathematically equivalent to all-pairs recall; refer to the accompanying audit for coverage limitations, including size-dependent weak-lane choices. Existing matching thresholds, classifications, File A-only outcome totals, File B references and exports remain unchanged.


### v6.32.83 — Desktop v6.33-compatible Excel export (2026-10-27)

- Preserves the existing Web backend classification and approved strict DOB
  validation. Does **not** replace the entire Web scorer with desktop v6.33;
  they have differences in behavior requiring separate recall validation.
- Ports the desktop v6.33 `export_results` XlsxWriter public design into a
  shared presentation module (`services/desktop_export_style.py`): five-column
  Summary, dark blue headers `#1F4E78`, duplicate family palette, DedupType
  colors, light blue Validated rows and pink Review rows.
- Both native XLSX and on-demand CSV-to-Excel conversion use the same public
  palette and formatting. Sequential export consolidates Process 1, Process 2,
  and Overall counts with the source File A classification invariant.
- The only public result columns are original File A headers in original
  order plus `DedupType`, `MatchPercentage`, `ConflictReason`. File B master
  rows can appear as reference rows in Duplicate Records, projected through
  the existing source-aware column mapper without adding File B-only headers.
- Reuses the desktop v6.33 `_simple_match_reason()` with optional precomputed
  caches and `_easy_duplicate_reason()` to explain original/reference names,
  DOB evidence and actual source row IDs. Retains Web-specific warning evidence
  for missing or conflicting fields.
- Ports desktop DOB `.0` display normalization for split Birth Month/Day/Year
  fields on exported copies (no modification to uploaded data).
- Preserves constant-memory XlsxWriter output, Zip64, safe temporary files,
  and Excel worksheet continuation instead of truncation.
- Keep the original private `database`, `certificates`, `.env`, Docker volume
  and uploads during upgrades. Local Windows Docker integration and 500K–1M-row
  benchmark remain to be verified in the target deployment.

### v6.32.84 — Header Mapping “+ Add condition” functional repair (2026-10-28)

- Root cause: the mapping popup disabled all Add Condition buttons while the
  draft editor was active; the click handler also returned for unsaved drafts.
- Buttons now open a per-header, inline condition editor **before** Save Changes.
  Add, edit, remove, enable, operator, value (text/number/date), paired File B
  header, action and AND/OR group settings use existing Rule Builder semantics.
- Save Changes atomically saves current File A header mappings and scoped rules
  to the **current user-owned session**. Refresh restores them only if the same
  uploaded files and selected worksheets are still active. Reusable profiles
  continue to use Rule Builder > Save current.
- Rule Builder now has **Save Rules for This Session** for edits performed there.
- Failed saves or network interruption preserve the draft and allow retry.
  Explicit 12-second save timeout, server-side validation and no duplicate Save.
- Source files, user-account database, Docker volumes, matching engine, export
  formatting, matching thresholds and File B reference-only behavior unchanged.
- Validated with browser DOM tests and isolated FastAPI/condition-evaluator
  tests. Real Windows Docker deployment and large-file processing are untested.

### v6.32.86 — Sequential group headings and Process 1 Keep One TRUE_DUPLICATE (2026-10-28)

- `DUPLICATE RECORDS` XLSX displays SECTION 1 (Process 1 Within File A),
  actual numbered duplicate groups, SECTION 2 (Clean File A vs File B),
  and independently restarted group numbering. `RECORDS FOR REVIEW` has
  corresponding Process 1/2 headings. The final four-sheet public workbook
  retains original File A header order and only the three approved result fields.
- Internal group IDs are streamed into a **private stage-only CSV metadata file**.
  This metadata never becomes a public workbook column or a final ZIP member.
  The combined public CSV sheets contain explicitly marked human-readable
  visual heading rows that must not be counted as beneficiary records.
- Settings adds `Keep One TRUE_DUPLICATE Record in Clean`, OFF by default.
  When enabled, within-file matching chooses the earliest *verified final_key*
  member per qualifying exact subgroup and keeps it in Clean. A display-only
  reference row appears in the Duplicate sheet, followed by the remaining
  duplicate members; reference rows do not affect counts.
- A retained representative from Process 1 still goes through Process 2.
  Process 2 never retains a matched File A row merely because of this checkbox.
  File B remains reference-only.
- Stage CSV continuations are read in order with schema verification; XLSX
  conversion writes clear dark-blue section headings and independently numbered
  group headers using constant-memory XlsxWriter.
- The original File A invariant is checked for both stages and the final export;
  no upload, database, or Docker volume migration is part of this update.
- The supplied historical example workbook was not available for byte-by-byte
  comparison in the current runtime; testing uses wholly synthetic small data.
  Full 500K–1M-row and live Windows Docker deployment are unverified.
