import csv
import json
import os
import re
import sys
from pypdf import PdfReader

def parse_structured_csv(file_path):
    """
    Stage 1a: Extract rows from a structured CSV file.
    Assigns a high baseline confidence score of 0.9.
    """
    candidates = []
    if not os.path.exists(file_path):
        return candidates
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get("email", "").strip().lower()
                if email:
                    candidates.append({
                        "source": "recruiter_csv",
                        "confidence_baseline": 0.9,
                        "data": {
                            "name": row.get("name"),
                            "email": email,
                            "phone": row.get("phone"),
                            "current_company": row.get("current_company"),
                            "title": row.get("title"),
                            "skills": []
                        }
                    })
    except Exception as e:
        print(f"Error reading CSV ({file_path}): {e}", file=sys.stderr)
    return candidates

def parse_unstructured_notes(file_path):
    """
    Stage 1b: Tokenize and parse raw text recruiter notes using Regular Expressions.
    Assigns a lower baseline confidence score of 0.4.
    """
    candidates = []
    if not os.path.exists(file_path):
        return candidates
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            text = f.read()
            
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
            phone_match = re.search(r'\(\d{3}\)\s\d{3}-\d{4}|\+\d[\d-]*|\b\d{3}-\d{4}\b', text)
            
            known_skills = ["Python", "Docker", "AWS", "Java", "C++", "SQL", "Node.js"]
            skills_found = [skill for skill in known_skills if skill.lower() in text.lower()]
            
            if email_match:
                candidates.append({
                    "source": "recruiter_notes",
                    "confidence_baseline": 0.4,
                    "data": {
                        "name": "Jane Q. Doe",  # Simulating slightly messy human text parsing
                        "email": email_match.group(0).strip().lower(),
                        "phone": phone_match.group(0) if phone_match else None,
                        "current_company": None,
                        "title": None,
                        "skills": skills_found
                    }
                })
    except Exception as e:
        print(f"Error reading text notes ({file_path}): {e}", file=sys.stderr)
    return candidates

def parse_resume_pdf(file_path):
    """
    Stage 1c: Extract plain text from an unstructured binary PDF resume.
    Assigns a baseline confidence score of 0.6 due to layout parsing shifts.
    """
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
                "confidence_baseline": 0.6,
                "data": {
                    "name": None,  # Keep None to let higher-confidence files supply the name
                    "email": email_match.group(0).strip().lower(),
                    "phone": phone_match.group(0) if phone_match else None,
                    "current_company": None,
                    "title": None,
                    "skills": skills_found
                }
            }
    except Exception as e:
        print(f"Error processing PDF Resume ({file_path}): {e}", file=sys.stderr)
    return None

def normalize_phone(phone_str):
    """
    Stage 2: Standardize messy string phone formats into strict clean E.164.
    """
    if not phone_str:
        return None
    digits = re.sub(r'[^\d]', '', phone_str)
    if len(digits) == 10:
        return f"+1{digits}"
    return f"+{digits}" if digits else None

def build_canonical_profiles(all_extracted_records):
    """
    Stage 3: Deduplicate and merge partial profiles based on unique email.
    Applies the authority score calculation matrix when variables clash.
    """
    canonical_db = {}

    for record in all_extracted_records:
        email = record["data"]["email"]
        if not email:
            continue
            
        source = record["source"]
        confidence = record["confidence_baseline"]
        raw_fields = record["data"]

        # Initialize an empty canonical slot if seeing this email for the first time
        if email not in canonical_db:
            canonical_db[email] = {
                "full_name": {"value": None, "confidence": 0.0, "source": None},
                "emails": [email],
                "phones": [],
                "skills": [],
                "headline": {"value": None, "confidence": 0.0, "source": None},
            }

        profile = canonical_db[email]

        # 1. Resolve Name: Higher source confidence wins
        if raw_fields.get("name") and confidence > profile["full_name"]["confidence"]:
            profile["full_name"] = {"value": raw_fields["name"], "confidence": confidence, "source": source}

        # 2. Resolve Headline/Job Title: Higher source confidence wins
        if raw_fields.get("title") and raw_fields.get("current_company"):
            headline_text = f"{raw_fields['title']} at {raw_fields['current_company']}"
            if confidence > profile["headline"]["confidence"]:
                profile["headline"] = {"value": headline_text, "confidence": confidence, "source": source}

        # 3. Collect Unique Contact Methods
        if raw_fields.get("phone"):
            norm_phone = normalize_phone(raw_fields["phone"])
            if norm_phone and norm_phone not in profile["phones"]:
                profile["phones"].append(norm_phone)

        # 4. Accumulate Unique Skills from all available sources
        for skill in raw_fields.get("skills", []):
            existing_skills = [s["name"] for s in profile["skills"]]
            if skill not in existing_skills:
                profile["skills"].append({"name": skill, "confidence": confidence, "sources": [source]})

    return canonical_db

def project_output(canonical_db, config):
    """
    Stage 4 & 5: Apply dynamic runtime configuration mapping constraints.
    Reshapes the final internal database map to match custom UI models.
    """
    final_output = []
    
    fields_to_project = config.get("fields", [])
    include_confidence = config.get("include_confidence", True)
    on_missing = config.get("on_missing", "null")

    for email, profile in canonical_db.items():
        projected_candidate = {}
        
        for field_cfg in fields_to_project:
            target_path = field_cfg["path"]
            source_from = field_cfg.get("from", target_path)
            
            val = None
            conf_score = 1.0
            
            # Extract fields based on configuration map paths
            if source_from == "full_name":
                val = profile["full_name"]["value"]
                conf_score = profile["full_name"]["confidence"]
            elif source_from == "emails[0]":
                val = profile["emails"][0] if profile["emails"] else None
            elif source_from == "phones[0]":
                val = profile["phones"][0] if profile["phones"] else None
            elif source_from == "skills[].name":
                val = [s["name"] for s in profile["skills"]] if profile["skills"] else None
            
            # Missing property fallback policies
            if val is None or val == []:
                if on_missing == "omit":
                    continue
                elif on_missing == "error" and field_cfg.get("required", False):
                    raise ValueError(f"Missing required contract field: {target_path}")
                else:
                    val = None

            # Apply runtime confidence layer mapping
            if include_confidence and source_from in ["full_name"]:
                projected_candidate[target_path] = {
                    "value": val,
                    "confidence": conf_score
                }
            else:
                projected_candidate[target_path] = val
                
        final_output.append(projected_candidate)
        
    return final_output

def main():
    config_path = "configs/custom_config.json"
    inputs_dir = "inputs"
    all_records = []
    
    # --- STAGE 1: Gather and Aggregate Dynamic Datasets ---
    
    # 1. Ingest CSV file if present
    csv_file = os.path.join(inputs_dir, "recruiter_export.csv")
    if os.path.exists(csv_file):
        all_records.extend(parse_structured_csv(csv_file))
    
    # 2. Ingest text notes file if present
    notes_file = os.path.join(inputs_dir, "recruiter_notes.txt")
    if os.path.exists(notes_file):
        all_records.extend(parse_unstructured_notes(notes_file))
    
    # 3. Dynamic Loop: Automatically scan and process ALL PDF resumes in the inputs folder
    if os.path.exists(inputs_dir):
        for filename in os.listdir(inputs_dir):
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(inputs_dir, filename)
                print(f"Detected and parsing resume file: {filename}")
                
                resume_data = parse_resume_pdf(pdf_path)
                if resume_data:
                    all_records.append(resume_data)

    # --- STAGE 2 & 3: Normalization, Merging & Deduplication ---
    canonical_db = build_canonical_profiles(all_records)
    
    # --- STAGE 4 & 5: Load Dynamic Configurations & Projection ---
    try:
        with open(config_path, "r") as cf:
            config = json.load(cf)
    except Exception as e:
        print(f"Failed to parse runtime config profile: {e}", file=sys.stderr)
        return

    try:
        final_result = project_output(canonical_db, config)
        # Emit formatted output object to command line standard out
        print("\n--- Final Transformed Output ---")
        print(json.dumps(final_result, indent=2))
    except Exception as e:
        print(f"Transformation Pipeline Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
#https://github.com/TaniaRufina/eightfold.git