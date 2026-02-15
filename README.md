# UD CRESP / DDOE K-16 Policy Analytics POC (Associate Data Scientist)

This repo is a compact, end-to-end proof-of-concept aligned with the University of Delaware CRESP role:
- co-managing statewide-style administrative + assessment data
- validating educator reporting accuracy with repeatable QA checks
- building an analysis-ready dataset
- answering policy-facing research questions with clear outputs (tables + brief)

Everything runs locally with **synthetic** (fake) data that resembles common K-12 administrative structures.

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Generates synthetic data, runs QA checks, builds analysis tables, and writes a short policy brief
python scripts/run_pipeline.py
```

## Outputs
- `data/raw/` synthetic inputs (students, educators, schools, assessments)
- `warehouse/out/` curated tables (fact/dim style)
- `reports/data_quality_report.json` QA results + flags
- `reports/policy_brief.pdf` 2-page brief with key findings from the synthetic run
- `reports/analysis_tables/` CSVs used in the brief

## What this demonstrates (mapped to the JD)
- **Database programming**: SQL schema + query examples (`sql/`)
- **Reporting accuracy**: educator QA checks (duplicates, missing certs, FTE totals, staffing ratios)
- **Program evaluation**: pre/post and subgroup comparisons with clear metrics
- **Policy writing**: short brief format used by agencies (methods + limitations + recommendations)

## Notes
- Replace synthetic inputs with real DDOE extracts by matching column names.
- The same QA framework can be scheduled (daily/weekly) and versioned in git.
