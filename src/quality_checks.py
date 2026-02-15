"""
Repeatable QA checks focused on educator reporting accuracy + basic data integrity.

These checks are meant to be simple, explainable, and easy to operationalize.
"""
from __future__ import annotations
from typing import Dict, Any, List
import numpy as np
import pandas as pd


def run_quality_checks(
    schools: pd.DataFrame,
    students: pd.DataFrame,
    student_school: pd.DataFrame,
    educators: pd.DataFrame,
    staffing: pd.DataFrame,
    assessments: pd.DataFrame,
) -> Dict[str, Any]:
    results: Dict[str, Any] = {"checks": [], "summary": {}}

    def add_check(name: str, passed: bool, detail: Dict[str, Any]):
        results["checks"].append({"name": name, "passed": bool(passed), "detail": detail})

    # 1) Primary key uniqueness
    add_check(
        "students_unique_id",
        students["student_id"].is_unique,
        {"duplicate_count": int(students["student_id"].duplicated().sum())},
    )
    add_check(
        "educators_unique_id",
        educators["educator_id"].is_unique,
        {"duplicate_count": int(educators["educator_id"].duplicated().sum())},
    )
    add_check(
        "schools_unique_id",
        schools["school_id"].is_unique,
        {"duplicate_count": int(schools["school_id"].duplicated().sum())},
    )

    # 2) Referential integrity
    missing_school_in_map = int(~student_school["school_id"].isin(schools["school_id"]).sum())
    add_check(
        "student_school_valid_school_id",
        missing_school_in_map == 0,
        {"missing_school_refs": missing_school_in_map},
    )
    missing_student_in_map = int(~student_school["student_id"].isin(students["student_id"]).sum())
    add_check(
        "student_school_valid_student_id",
        missing_student_in_map == 0,
        {"missing_student_refs": missing_student_in_map},
    )

    # 3) Staffing: FTE sanity
    staffing_fte_by_educ = staffing.groupby("educator_id")["fte"].sum()
    over_1 = staffing_fte_by_educ[staffing_fte_by_educ > 1.05]
    add_check(
        "educator_total_fte_leq_1_05",
        len(over_1) == 0,
        {"violations": int(len(over_1)), "max_fte": float(staffing_fte_by_educ.max())},
    )

    # 4) Certification completeness for teachers
    teachers = educators[educators["role"] == "teacher"]
    uncert = int((teachers["certification"] == "none").sum())
    uncert_rate = float(uncert / max(1, len(teachers)))
    # policy choice: flag if >2% teachers have no certification (placeholder threshold)
    add_check(
        "teacher_certification_none_rate_leq_0_02",
        uncert_rate <= 0.02,
        {"teacher_count": int(len(teachers)), "none_cert_count": uncert, "none_cert_rate": uncert_rate},
    )

    # 5) Assessment coverage: each student should have 2 records (ELA + Math) in spring
    spring = assessments[(assessments["term"] == "spring")]
    cnt = spring.groupby("student_id")["subject"].nunique()
    missing_subj = int((cnt < 2).sum())
    add_check(
        "assessment_coverage_two_subjects_spring",
        missing_subj == 0,
        {"students_missing_subject": missing_subj},
    )

    # 6) Student-to-teacher ratio per school (rough, using teacher FTE)
    # join student counts
    student_counts = student_school.groupby("school_id")["student_id"].nunique()
    teacher_fte = staffing.merge(educators[["educator_id", "role"]], on="educator_id", how="left")
    teacher_fte = teacher_fte[teacher_fte["role"] == "teacher"].groupby("school_id")["fte"].sum()
    ratio = (student_counts / teacher_fte.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    # flag extreme ratios (>35 students per teacher FTE), placeholder
    extreme = ratio[ratio > 35]
    add_check(
        "students_per_teacher_fte_leq_35",
        int(len(extreme)) == 0,
        {"extreme_schools": int(len(extreme)), "max_ratio": float(np.nanmax(ratio)) if ratio.notna().any() else None},
    )

    # summary
    results["summary"] = {
        "total_checks": len(results["checks"]),
        "passed_checks": int(sum(1 for c in results["checks"] if c["passed"])),
        "failed_checks": int(sum(1 for c in results["checks"] if not c["passed"])),
    }
    return results
