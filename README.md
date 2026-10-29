# CrossMatch Browser

**Version:** 6.32.91  
**Application Type:** Web-Based Deduplication, Cross-Matching, and Data Validation System  
**Technology:** Python, FastAPI, JavaScript, HTML, CSS, SQLite, and Docker

## Project Overview

CrossMatch Browser is a web-based data processing application designed to detect duplicate records, identify potential matches between datasets, validate beneficiary information, and generate organized Excel reports.

The system supports different data structures, configurable validation rules, and large CSV/Excel datasets.

It is designed to assist authorized personnel with data quality management, duplicate detection, cross-matching, and manual verification.

## Main Features

### 1. Data Upload and Header Mapping

- Upload Excel and CSV datasets.
- Select Excel worksheets.
- Automatically detect name and birthdate headers.
- Manually correct header mappings.
- Support different column names and structures.

### 2. Deduplication and Cross-Matching

The application supports three processing modes:

**File A Only — Self-Deduplication**

Detect duplicate records within File A.

**File A vs File B — Cross-Matching**

Compare File A against File B, using File B strictly as reference data.

**Sequential Processing**

- Process 1: Self-deduplication of File A.
- Process 2: Cross-match eligible Clean File A records against File B.
- Final: Consolidate File A classifications.

### 3. Duplicate Detection

The system supports:

- TRUE_DUPLICATE
- TRUE_SWAP_DUPLICATE
- FUZZY_DUPLICATE
- FUZZY_SWAP_DUPLICATE
- Similar-name matching
- Filipino compound-name handling
- First, middle, last, and suffix comparisons
- Birthdate validation and comparison

Matching uses configurable similarity thresholds and established Name + DOB scoring rules.

### 4. Keep One TRUE_DUPLICATE in Clean

Enabled by default for new configurations.

During File A self-deduplication, one eligible representative from each verified exact-duplicate subgroup can remain in Clean.

This setting does not apply to File A vs File B cross-matching.

### 5. Unified Condition Builder

- Simple and Advanced modes
- Process 1 and Process 2 conditions
- Text, number, and date comparisons
- File A and File B field comparisons
- AND/OR conditions
- Saved rule profiles
- Configurable DSWD program examples
- Rule testing and validation
- Duplicate, Clean, Review, and Finding Only actions subject to validation safeguards

Program templates are configurable examples and do not represent official eligibility policies.

### 6. Excel Reporting

Generates the following worksheets:

1. SUMMARY
2. VALIDATED RECORDS
3. DUPLICATE RECORDS
4. RECORDS FOR REVIEW

Reports preserve original File A headers and include:

- DedupType
- MatchPercentage
- ConflictReason

Sequential reports distinguish Process 1 and Process 2 and use background colors to identify duplicate groups.

### 7. User Management

- User registration and login
- Administrator approval
- User account management
- Session management
- Saved settings and rule profiles

## Application Architecture

```text
Web Browser
     |
     v
FastAPI Backend
     |
     v
Upload and Header Mapping
     |
     v
Condition Validation
     |
     v
Python Deduplication Engine
     |
     v
File A Classification
     |
     v
Excel Report Generation
     |
     v
Download Results
```

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python / FastAPI |
| Frontend | HTML / CSS / JavaScript |
| Matching | Python / RapidFuzz |
| Processing Storage | SQLite |
| Excel Generation | XlsxWriter |
| Deployment | Docker |
| Web Proxy | Nginx |
| Source Control | GitHub |

## Repository Structure

```text
CrossMatch_Web_FAST/
├── engine/
├── services/
├── static/
├── templates/
├── nginx/
├── deploy/
├── docs/
├── app.py
├── config.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── docker-compose.server.yml
└── README.md
```

## Deployment

The application currently supports local development using Docker Desktop with Linux containers on Windows 11.

For Windows Server 2022 deployment, the prepared server configuration targets an IT-managed Linux virtual machine with Docker Engine.

Production deployment requires approved server configuration, secure HTTPS access, protected persistent storage, and environment-specific testing.

## Data Privacy and Security

This repository must contain application source code only.

Do not commit:

- Beneficiary Excel or CSV records
- Production databases
- Passwords and authentication secrets
- Private certificates
- Environment files containing credentials
- Confidential processing results

Access to the deployed application should be restricted to authorized personnel.

## Development Status

**Current Version: 6.32.91**

The application includes deduplication, cross-matching, rule configuration, user management, and Excel reporting functionality.

Local synthetic-data testing has been performed for selected workflows. Production-scale performance, matching recall, and Windows Server deployment require further verification.

## Project Objective

Provide a centralized and configurable data validation and cross-matching application that can support different DSWD program datasets while maintaining consistent matching rules, traceable results, and reliable record classification.
