import streamlit as st
import os
import json
import sys
# Import your existing pipeline functions from main.py
from main import (
    parse_structured_csv, 
    parse_unstructured_notes, 
    parse_ats_json, 
    parse_resume_pdf, 
    build_canonical_profiles, 
    project_output
)

# Page configuration
st.set_page_config(page_title="Candidate Data Transformer", page_icon="⚡", layout="wide")

st.title("⚡ Multi-Source Candidate Data Transformer")
st.caption("Eightfold Engineering Intern Assessment — Production Ingestion Pipeline")
st.markdown("---")

# Layout columns
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("⚙️ Pipeline Controls")
    inputs_dir = st.text_input("Data Inputs Directory", value="inputs")
    config_path = st.text_input("Engine Configuration File", value="configs/custom_config.json")
    
    run_pipeline = st.button("🚀 Execute Data Transformer", type="primary", use_container_width=True)

with col2:
    st.subheader("📊 Execution Stream & Output")
    
    if run_pipeline:
        if not os.path.exists(inputs_dir):
            st.error(f"Target inputs directory '{inputs_dir}' not found!")
        else:
            with st.spinner("Processing ingestion streams and merging profiles..."):
                all_records = []
                
                # Ingestion
                csv_file = os.path.join(inputs_dir, "recruiter_export.csv")
                notes_file = os.path.join(inputs_dir, "recruiter_notes.txt")
                ats_file = os.path.join(inputs_dir, "ats_data.json")
                
                if os.path.exists(csv_file): all_records.extend(parse_structured_csv(csv_file))
                if os.path.exists(notes_file): all_records.extend(parse_unstructured_notes(notes_file))
                if os.path.exists(ats_file): all_records.extend(parse_ats_json(ats_file))
                
                # Dynamic PDF scan
                for filename in os.listdir(inputs_dir):
                    if filename.lower().endswith(".pdf"):
                        pdf_path = os.path.join(inputs_dir, filename)
                        all_records.extend([parse_resume_pdf(pdf_path) or {}])
                all_records = [r for r in all_records if r]
                
                # Core processing & merging
                canonical_db = build_canonical_profiles(all_records)
                
                # Read configuration rules
                try:
                    with open(config_path, "r") as cf:
                        config = json.load(cf)
                except Exception as e:
                    st.error(f"Configuration Loading Failed: {e}")
                    st.stop()
                    
                # Projection and Validation
                try:
                    final_result = project_output(canonical_db, config)
                    
                    st.success(f"Successfully processed records into {len(final_result)} deduplicated profiles!")
                    
                    # Modern code display format
                    json_string = json.dumps(final_result, indent=2)
                    st.code(json_string, language="json")
                    
                    st.markdown("---")
                    # Native high-performance download utility
                    st.download_button(
                        label="📥 Download Canonical JSON Profile",
                        data=json_string,
                        file_name="canonical_profiles.json",
                        mime="application/json",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Pipeline Adjudication Failure: {e}")
    else:
        st.info("Click 'Execute Data Transformer' to process files, view trace maps, and unlock the download link.")