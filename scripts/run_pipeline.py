"""
End-to-end runner:
1) generate synthetic raw data
2) run QA checks (educator accuracy + integrity)
3) build curated tables (warehouse/out)
4) run policy analyses and write a 2-page policy brief PDF

Run:
  python scripts/run_pipeline.py
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

from src.generate_data import generate_all, GenConfig
from src.quality_checks import run_quality_checks
from src.analysis import proficiency_by_subgroup, staffing_ratio_table, ratio_vs_proficiency

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "warehouse" / "out"
REPORTS = ROOT / "reports"
TABLES = REPORTS / "analysis_tables"

def _load_raw():
    schools = pd.read_csv(RAW / "schools.csv")
    students = pd.read_csv(RAW / "students.csv")
    student_school = pd.read_csv(RAW / "student_school.csv")
    educators = pd.read_csv(RAW / "educators.csv")
    staffing = pd.read_csv(RAW / "staffing.csv")
    assessments = pd.read_csv(RAW / "assessments.csv")
    return schools, students, student_school, educators, staffing, assessments

def _write_policy_brief(path, qa, gap_tbl, ratio_prof_tbl):
    # lightweight PDF with key findings
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch

    c = canvas.Canvas(str(path), pagesize=letter)
    W,H = letter

    def para(txt, y, size=10, leading=13, maxw=6.9*inch):
        c.setFont("Helvetica", size)
        x = 0.9*inch
        words = txt.split()
        line = ""
        lines=[]
        for w0 in words:
            t=(line+" "+w0).strip()
            if c.stringWidth(t, "Helvetica", size) <= maxw:
                line=t
            else:
                lines.append(line); line=w0
        if line: lines.append(line)
        for ln in lines:
            c.drawString(x,y,ln); y-=leading
        return y

    y = H - 0.85*inch
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.9*inch, y, "Policy Brief (POC): K-12 Staffing + Achievement Indicators")
    y -= 0.35*inch
    y = para(
        "This is a synthetic demonstration of an analytics workflow used in state education agencies: "
        "validating educator reporting data, constructing analysis-ready tables, and producing policy-facing indicators "
        "for staffing and student outcomes. Results below are illustrative only.",
        y
    )

    y -= 0.1*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.9*inch, y, "Data quality snapshot")
    y -= 0.2*inch
    summ = qa["summary"]
    y = para(
        f"Checks run: {summ['total_checks']}. Passed: {summ['passed_checks']}. Failed: {summ['failed_checks']}. "
        "Failed checks should be triaged with targeted follow-ups (e.g., certification records, staffing FTE anomalies).",
        y
    )

    # show top failed checks (if any)
    failed = [c0 for c0 in qa["checks"] if not c0["passed"]][:3]
    if failed:
        y -= 0.05*inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.9*inch, y, "Top flags:")
        y -= 0.18*inch
        c.setFont("Helvetica", 10)
        for f in failed:
            c.drawString(0.95*inch, y, f"• {f['name']}")
            y -= 0.16*inch

    y -= 0.08*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.9*inch, y, "Proficiency gaps (spring)")
    y -= 0.2*inch

    # small table-like text (top 6 rows)
    show = gap_tbl.copy()
    show["proficiency_group_1"] = (show["proficiency_group_1"]*100).round(1)
    show["proficiency_group_0"] = (show["proficiency_group_0"]*100).round(1)
    show["gap_group0_minus_group1"] = (show["gap_group0_minus_group1"]*100).round(1)
    c.setFont("Helvetica", 9)
    c.drawString(0.9*inch, y, "Subject | Group | Group=1 Proficiency | Group=0 Proficiency | Gap (pp)")
    y -= 0.16*inch
    for _, r in show.head(8).iterrows():
        c.drawString(0.9*inch, y, f"{r['subject']:>4} | {r['group']:<4} | {r['proficiency_group_1']:>6}% | {r['proficiency_group_0']:>6}% | {r['gap_group0_minus_group1']:>5}")
        y -= 0.15*inch

    c.showPage()

    y = H - 0.85*inch
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.9*inch, y, "Staffing ratios and outcomes (illustrative)")
    y -= 0.35*inch

    corr = ratio_prof_tbl.attrs.get("corr_students_per_teacher_vs_proficiency")
    y = para(
        "We computed a school-level students-per-teacher (FTE) indicator and compared it with average proficiency. "
        "This is an association, not causal; it highlights schools for deeper diagnostic review and potential program evaluation.",
        y
    )
    y -= 0.1*inch
    y = para(
        f"Correlation (students/teacher FTE vs proficiency): {corr:.3f}" if corr is not None else
        "Correlation (students/teacher FTE vs proficiency): n/a",
        y
    )
    y -= 0.1*inch

    # show top 10 highest ratios
    top = ratio_prof_tbl.sort_values("students_per_teacher_fte", ascending=False).head(10).copy()
    c.setFont("Helvetica", 9)
    c.drawString(0.9*inch, y, "Top schools by students per teacher FTE (for follow-up)")
    y -= 0.16*inch
    c.drawString(0.9*inch, y, "school_id | students | teacher_fte | students_per_teacher_fte | avg_proficiency")
    y -= 0.16*inch
    for _, r in top.iterrows():
        c.drawString(0.9*inch, y, f"{int(r['school_id']):>7} | {int(r['n_students']):>8} | {r['teacher_fte']:.1f} | {r['students_per_teacher_fte']:.1f} | {r['avg_proficiency']:.3f}")
        y -= 0.15*inch

    y -= 0.08*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.9*inch, y, "Recommended next steps")
    y -= 0.2*inch
    y = para(
        "1) Operationalize QA checks as a scheduled job with owner-based triage. "
        "2) Define a small set of stable, documented metrics (staffing ratios, assessment coverage, subgroup gaps). "
        "3) For prioritized initiatives, design an evaluation plan (comparison groups, pre/post windows, robustness checks).",
        y
    )

    c.save()

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)

    # 1) generate data
    generate_all(RAW, GenConfig())

    # 2) load raw
    schools, students, student_school, educators, staffing, assessments = _load_raw()

    # 3) QA
    qa = run_quality_checks(schools, students, student_school, educators, staffing, assessments)
    with open(REPORTS / "data_quality_report.json", "w", encoding="utf-8") as f:
        json.dump(qa, f, indent=2)

    # 4) curated tables (simple "warehouse")
    # dim/fact-like outputs
    schools.to_csv(OUT / "dim_school.csv", index=False)
    students.to_csv(OUT / "dim_student.csv", index=False)
    educators.to_csv(OUT / "dim_educator.csv", index=False)
    staffing.to_csv(OUT / "fct_staffing.csv", index=False)
    assessments.to_csv(OUT / "fct_assessment.csv", index=False)
    student_school.to_csv(OUT / "bridge_student_school.csv", index=False)

    # 5) analyses
    gap_tbl = proficiency_by_subgroup(assessments, students)
    ratio_tbl = staffing_ratio_table(student_school, staffing, educators)
    ratio_prof_tbl = ratio_vs_proficiency(ratio_tbl, assessments, student_school)

    gap_tbl.to_csv(TABLES / "proficiency_gaps.csv", index=False)
    ratio_prof_tbl.to_csv(TABLES / "staffing_ratio_vs_proficiency.csv", index=False)

    # 6) brief
    _write_policy_brief(REPORTS / "policy_brief.pdf", qa, gap_tbl, ratio_prof_tbl)

    print("Done.")
    print("Key outputs:")
    print(" - reports/data_quality_report.json")
    print(" - reports/policy_brief.pdf")
    print(" - reports/analysis_tables/*.csv")
    print(" - warehouse/out/*.csv")

if __name__ == "__main__":
    main()

