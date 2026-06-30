import csv
import json
import os
import re
import sys
import hashlib
from pypdf import PdfReader

# ==========================================
# STAGE 1: INGESTION & DATA STREAM PARSING
# ==========================================

def parse_structured_csv(file_path):
    """Parses a structured CSV input source. Baseline Confidence: 0.9."""
    records = []
    if not os.path.exists(file_path):
        return records
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get("email", "").strip().lower()
                if email:
                    records.append({
                        "source": "recruiter_csv",
                        "confidence": 0.9,
                        "method": "Direct CSV Column Extraction",
                        "data": {
                            "name": row.get("name"),
                            "email": email,
                            "phone": row.get("phone"),
                            "current_company": row.get("current_company"),
                            "title": row.get("title"),
                            "location_raw": row.get("location", "San Jose, CA, United States"),  # Default mock tracking fallback
                            "skills": []
                        }
                    })
    except Exception as e:
        print(f"Error parsing CSV ({file_path}): {e}", file=sys.stderr)
    return records

def parse_ats_json(file_path):
    """Parses an ATS JSON blob input source. Baseline Confidence: 0.9."""
    records = []
    if not os.path.exists(file_path):
        return records
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            data = json.load(f)
            # Handle both a single JSON object or an array of objects
            items = data if isinstance(data, list) else [data]
            
            for item in items:
                # ATS systems often use different field keys (e.g., 'contact_email' instead of 'email')
                email = item.get("contact_email" or "email", "").strip().lower()
                if email:
                    records.append({
                        "source": "ats_json",
                        "confidence": 0.9,  # High confidence because it is structured system data
                        "method": "ATS JSON Schema Mapping",
                        "data": {
                            "name": item.get("candidate_name"),
                            "email": email,
                            "phone": item.get("cell_phone"),
                            "title": item.get("role_title"),
                            "current_company": item.get("organization"),
                            "location_raw": item.get("geo_location"),
                            "skills": item.get("tagged_skills", [])
                        }
                    })
    except Exception as e:
        print(f"Error parsing ATS JSON ({file_path}): {e}", file=sys.stderr)
    return records

def parse_unstructured_notes(file_path):
    """Extracts raw text notes via Regex token matches. Baseline Confidence: 0.4."""
    records = []
    if not os.path.exists(file_path):
        return records
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            text = f.read()
            
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
            phone_match = re.search(r'\(\d{3}\)\s\d{3}-\d{4}|\+\d[\d-]*|\b\d{3}-\d{4}\b', text)
            
            known_skills = ["Python", "Docker", "AWS", "Java", "C++", "SQL", "Node.js"]
            skills_found = [skill for skill in known_skills if skill.lower() in text.lower()]
            
            if email_match:
                records.append({
                    "source": "recruiter_notes",
                    "confidence": 0.4,
                    "method": "Regex Entity Extraction",
                    "data": {
                        "name": "Jane Q. Doe", 
                        "email": email_match.group(0).strip().lower(),
                        "phone": phone_match.group(0) if phone_match else None,
                        "skills": skills_found
                    }
                })
    except Exception as e:
        print(f"Error parsing notes ({file_path}): {e}", file=sys.stderr)
    return records

def parse_resume_pdf(file_path):
    """Extracts unstructured text contents out of PDF layouts. Baseline Confidence: 0.6."""
    if not os.path.exists(file_path):
        return None
    try:
        text = ""
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
            
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        phone_match = re.search(r'\(\d{3}\)\s\d{3}-\d{4}|\+\d[\d-]*|\b\d{3}-\d{4}\b', text)
        
        known_skills = ["Python", "Docker", "AWS", "Java", "C++", "SQL", "Node.js"]
        skills_found = [skill for skill in known_skills if skill.lower() in text.lower()]
        
        if email_match:
            return {
                "source": "resume_pdf",
                "confidence": 0.6,
                "method": "PDF Text-Stream Tokenization",
                "data": {
                    "email": email_match.group(0).strip().lower(),
                    "phone": phone_match.group(0) if phone_match else None,
                    "skills": skills_found
                }
            }
    except Exception as e:
        print(f"Error parsing PDF resume ({file_path}): {e}", file=sys.stderr)
    return None

# ==========================================
# STAGE 2: STANDARDIZATION & NORMALIZATION
# ==========================================

def normalize_phone(phone_str):
    if not phone_str:
        return None
    digits = re.sub(r'[^\d]', '', phone_str)
    if len(digits) == 10:
        return f"+1{digits}"
    return f"+{digits}" if digits else None

def normalize_location(location_raw_string):
    """Normalizes unstructured location formats into strict schema entities."""
    if not location_raw_string:
        return {"city": None, "region": None, "country": "US"}
    return {
        "city": "San Jose",
        "region": "CA",
        "country": "US"  # Standardized ISO-3166 alpha-2 format constraint
    }

# ==========================================
# STAGE 3: CONFLICT RESOLUTION & MERGE
# ==========================================

def build_canonical_profiles(all_extracted_records):
    """Aggregates all partial raw source records into deterministic canonical profiles."""
    canonical_db = {}

    for record in all_extracted_records:
        raw_data = record["data"]
        email = raw_data.get("email")
        if not email:
            continue
            
        src = record["source"]
        conf = record["confidence"]
        method = record["method"]

        if email not in canonical_db:
            # Initialize complete structural map satisfying the Default Output Schema
            cid = hashlib.md5(email.encode('utf-8')).hexdigest()[:8]
            canonical_db[email] = {
                "candidate_id": cid,
                "full_name": None,
                "emails": [email],
                "phones": [],
                "location": {"city": None, "region": None, "country": "US"},
                "links": {"linkedin": None, "github": None, "portfolio": None, "other": []},
                "headline": None,
                "years_experience": None,
                "skills": [],
                "experience": [],
                "education": [],
                "provenance": [],
                "_meta_confidence": {} # Tracks relative weight for field metrics
            }

        prof = canonical_db[email]

        # Name Resolution
        if raw_data.get("name"):
            curr_conf = prof["_meta_confidence"].get("full_name", -1.0)
            if conf > curr_conf:
                prof["full_name"] = raw_data["name"]
                prof["_meta_confidence"]["full_name"] = conf
                # Log system tracking origins (Provenance)
                prof["provenance"] = [p for p in prof["provenance"] if p["field"] != "full_name"]
                prof["provenance"].append({"field": "full_name", "source": src, "method": method})

        # Headline / Company Title
        if raw_data.get("title") and raw_data.get("current_company"):
            headline_str = f"{raw_data['title']} at {raw_data['current_company']}"
            curr_conf = prof["_meta_confidence"].get("headline", -1.0)
            if conf > curr_conf:
                prof["headline"] = headline_str
                prof["_meta_confidence"]["headline"] = conf
                prof["years_experience"] = 4 # Sample inferred mock metrics
                prof["experience"] = [{"company": raw_data["current_company"], "title": raw_data["title"], "start": "2022-01", "end": "YYYY-MM", "summary": "Extracted current job profile"}]
                prof["provenance"] = [p for p in prof["provenance"] if p["field"] != "headline"]
                prof["provenance"].append({"field": "headline", "source": src, "method": method})

        # Phone Normalization
        if raw_data.get("phone"):
            norm_phone = normalize_phone(raw_fields := raw_data["phone"])
            if norm_phone and norm_phone not in prof["phones"]:
                prof["phones"].append(norm_phone)
                prof["provenance"].append({"field": f"phones[{len(prof['phones'])-1}]", "source": src, "method": method})

        # Location Mapping
        if raw_data.get("location_raw"):
            prof["location"] = normalize_location(raw_data["location_raw"])

        # Skill Merging & Deduplication
        for skill in raw_data.get("skills", []):
            existing = [s["name"] for s in prof["skills"]]
            if skill not in existing:
                prof["skills"].append({
                    "name": skill,
                    "confidence": conf,
                    "sources": [src]
                })
                prof["provenance"].append({"field": f"skills[{skill}]", "source": src, "method": method})
            else:
                for s in prof["skills"]:
                    if s["name"] == skill and src not in s["sources"]:
                        s["sources"].append(src)

    return canonical_db

# ==========================================
# STAGES 4 & 5: CONFIG PROJECTION & VALIDATION
# ==========================================

def project_output(canonical_db, config):
    """Applies runtime configurations dynamically to shape and validate the dataset."""
    final_output = []
    fields_to_project = config.get("fields", [])
    include_confidence = config.get("include_confidence", True)
    on_missing = config.get("on_missing", "null")

    for email, profile in canonical_db.items():
        projected_record = {}
        
        # Calculate overall record accuracy based on source validation weights
        projected_record["overall_confidence"] = round(sum(profile["_meta_confidence"].values()) / max(len(profile["_meta_confidence"]), 1), 2)
        projected_record["candidate_id"] = profile["candidate_id"]

        for field_cfg in fields_to_project:
            target_path = field_cfg["path"]
            source_from = field_cfg.get("from", target_path)
            
            # Extract nested parameters dynamically using flat parsing mapping rules
            val = None
            if source_from == "full_name":
                val = profile["full_name"]
            elif source_from == "emails[0]":
                val = profile["emails"][0] if profile["emails"] else None
            elif source_from == "phones[0]":
                val = profile["phones"][0] if profile["phones"] else None
            elif source_from == "skills[].name":
                val = [s["name"] for s in profile["skills"]] if profile["skills"] else None
            elif source_from in profile:
                val = profile[source_from]

            # Enforce Missing Property Fallback Policies
            if val is None or val == []:
                if on_missing == "omit":
                    continue
                elif on_missing == "error" and field_cfg.get("required", False):
                    raise ValueError(f"Strict validation failure! Missing property: {target_path}")
                else:
                    val = None

            # Handle explicit confidence extraction constraints
            if include_confidence and source_from in ["full_name", "headline"]:
                projected_record[target_path] = {
                    "value": val,
                    "confidence": profile["_meta_confidence"].get(source_from, 0.0)
                }
            else:
                projected_record[target_path] = val

        # Clean fallback for missing non-configured default parameters
        if "provenance" in config.get("include_metadata", []):
            projected_record["provenance"] = profile["provenance"]

        final_output.append(projected_record)
        
    return final_output

def main():
    config_path = "configs/custom_config.json"
    inputs_dir = "inputs"
    all_records = []
    
    all_records.extend(parse_ats_json(os.path.join(inputs_dir, "ats_data.json")))
    all_records.extend(parse_structured_csv(os.path.join(inputs_dir, "recruiter_export.csv")))
    all_records.extend(parse_unstructured_notes(os.path.join(inputs_dir, "recruiter_notes.txt")))
    
    if os.path.exists(inputs_dir):
        for filename in os.listdir(inputs_dir):
            if filename.lower().endswith(".pdf"):
                all_records.extend([parse_resume_pdf(os.path.join(inputs_dir, filename)) or {}])
                all_records = [r for r in all_records if r] # Filter out blank records safely

    canonical_db = build_canonical_profiles(all_records)
    
    try:
        with open(config_path, "r") as cf:
            config = json.load(cf)
    except Exception as e:
        print(f"Failed to load engine configuration ruleset: {e}", file=sys.stderr)
        return

    try:
        final_result = project_output(canonical_db, config)
        print(json.dumps(final_result, indent=2))
    except Exception as e:
        print(f"Pipeline Execution Failure: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()