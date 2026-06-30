# Multi-Source Candidate Data Transformer Engine

A production-grade, deterministic data engineering pipeline built in Python to ingest, normalize, de-duplicate, and transform fragmented candidate profiles from multiple disparate sources into a uniform, configurable canonical structure.

## Core Features
* **Multi-Source Ingestion:** Concurrently processes structured database targets (`.csv`, `.json` ATS blobs) and unstructured text-stream elements (`.txt` recruiter field notes, `.pdf` resumes).
* **Deterministic Conflict Resolution:** Employs a strict Source Authority Confidence Matrix ($Confidence_{incoming} > Confidence_{existing}$) to dynamically arbitrate cross-source field clashes using unique email address anchors.
* **Traceable Data Provenance:** Tracks an immutable digital audit footprint `[{ field, source, method }]` for every single property field to ensure 100% explainable pipeline transparency.
* **Dynamic Runtime Projection:** Reshapes final output JSON data payloads dynamically on the fly based on an external layout schema matrix (`configs/custom_config.json`) without mutating core state-layer mechanics.

---

## Project Structure
```text
D:\eightfold-transformer\
├── configs/
│   └── custom_config.json      # Dynamic runtime configuration and mapping ruleset
├── inputs/
│   ├── recruiter_export.csv    # Sample structured CSV dataset
│   ├── ats_data.json           # High-priority automated ATS schema blob
│   └── recruiter_notes.txt     # Sample unstructured conversational field notes
├── main.py                     # Primary pipeline execution engine (Headless CLI)
├── app.py                      # Interactive Streamlit Web UI dashboard (Presentation layer)
├── output.json                 # <--- ADD THIS LINE: Final produced output payload
└── requirements.txt            # Project system dependencies list

---

## 🚀 Execution Guide

#1. Environment Setup
Install the necessary processing utilities and UI modules via your terminal package manager:

Bash
pip install -r requirements.txt

#2. Runtime Execution Frameworks
Mode A: Headless Production Pipeline (Command Line)
To execute the engine natively through the system console and stream the finalized canonical JSON footprint directly to standard output (stdout):

Bash
python main.py

#Mode B: Interactive Streamlit Dashboard (Visual UX)
To launch the interactive presentation workspace, trigger execution loops visually, examine real-time data integration maps, and download compiled JSON schema results with one click:

Bash
streamlit run app.py