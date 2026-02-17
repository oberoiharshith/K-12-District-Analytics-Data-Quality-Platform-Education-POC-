"""
Policy-facing analyses using curated tables.

Focus areas:
- proficiency gaps by subgroup
- staffing ratios vs outcomes (simple association)
- pre/post style framing (synthetic baseline vs current year)
"""
from __future__ import annotations
from typing import Dict, Tuple
import numpy as np
import pandas as pd
from scipy import stats


def proficiency_by_subgroup(assessments: pd.DataFrame, students: pd.DataFrame) -> pd.DataFrame:
    df = assessments.merge(students, on="student_id", how="left")
    df = df[df["term"] == "spring"].copy()

    out = []
    for subj in ["ela", "math"]:
        d = df[df["subject"] == subj]
        for grp, col in [("FRPL", "frpl_flag"), ("ELL", "ell_flag"), ("IEP", "iep_flag")]:
            p1 = d.loc[d[col] == 1, "proficient_flag"].mean()
            p0 = d.loc[d[col] == 0, "proficient_flag"].mean()
            out.append({
                "subject": subj,
                "group": grp,
                "proficiency_group_1": float(p1),
                "proficiency_group_0": float(p0),
                "gap_group0_minus_group1": float(p0 - p1),
            })
    return pd.DataFrame(out)


def staffing_ratio_table(student_school: pd.DataFrame, staffing: pd.DataFrame, educators: pd.DataFrame) -> pd.DataFrame:
    student_counts = student_school.groupby("school_id")["student_id"].nunique().rename("n_students")
    teacher_fte = staffing.merge(educators[["educator_id", "role"]], on="educator_id", how="left")
    teacher_fte = teacher_fte[teacher_fte["role"] == "teacher"].groupby("school_id")["fte"].sum().rename("teacher_fte")
    out = pd.concat([student_counts, teacher_fte], axis=1).reset_index()
    out["students_per_teacher_fte"] = out["n_students"] / out["teacher_fte"].replace(0, np.nan)
    return out


def ratio_vs_proficiency(
    ratio_tbl: pd.DataFrame,
    assessments: pd.DataFrame,
    student_school: pd.DataFrame,
) -> pd.DataFrame:
    # school-level proficiency (spring, combined subjects)
    spring = assessments[assessments["term"] == "spring"].copy()
    school_prof = spring.groupby("school_id")["proficient_flag"].mean().rename("avg_proficiency")
    df = ratio_tbl.merge(school_prof.reset_index(), on="school_id", how="left")
    # simple correlation
    valid = df.dropna(subset=["students_per_teacher_fte", "avg_proficiency"])
    corr = np.corrcoef(valid["students_per_teacher_fte"], valid["avg_proficiency"])[0,1] if len(valid) > 2 else np.nan
    df.attrs["corr_students_per_teacher_vs_proficiency"] = float(corr) if corr==corr else None
    return df

