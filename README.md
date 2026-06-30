# Multi-Source Candidate Data Transformer Engine

A deterministic data processing pipeline built in Python to ingest, normalize, de-duplicate, and transform fragmented candidate profiles from multiple disparate sources into a uniform, configurable canonical structure.

## Core Features
* **Multi-Source Ingestion:** Supports structured (`.csv`) and unstructured (`.txt` notes) data streams.
* **Deterministic Conflict Resolution:** Employs a strict Source Authority Confidence Matrix where high-integrity sources automatically override speculative extractions.
* **Dynamic Runtime Projection:** Reshapes final output JSON formats dynamically based on an external runtime configuration profile without modifying core engineering logic.

---

## Project Structure
```text
D:\eightfold-transformer\
├── configs/
│   └── custom_config.json      # Dynamic runtime configuration rules
├── inputs/
│   ├── recruiter_export.csv    # Sample structured input source
│   └── recruiter_notes.txt     # Sample unstructured input source
├── main.py                     # Primary execution pipeline engine
└── requirements.txt            # Project dependencies list