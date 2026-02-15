"""
Synthetic statewide-style K-12 administrative and assessment data generator.

The goal is not realism to the decimal; it's to create plausible structure:
- schools, students, educators
- staffing assignments with FTE
- assessments (ELA/Math) with subgroup gaps

Outputs CSVs to data/raw/.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd


@dataclass
class GenConfig:
    seed: int = 7
    n_districts: int = 12
    n_schools: int = 90
    n_students: int = 42000
    n_educators: int = 5200
    school_year: int = 2025


def generate_all(out_dir: Path, cfg: GenConfig) -> None:
    rng = np.random.default_rng(cfg.seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    # schools
    district_ids = rng.integers(1, cfg.n_districts + 1, cfg.n_schools)
    levels = rng.choice(["elementary", "middle", "high"], size=cfg.n_schools, p=[0.5, 0.28, 0.22])
    urban = rng.choice(["urban", "suburban", "rural"], size=cfg.n_schools, p=[0.34, 0.46, 0.20])
    schools = pd.DataFrame({
        "school_id": np.arange(1001, 1001 + cfg.n_schools),
        "district_id": district_ids,
        "school_name": [f"School {i}" for i in range(1, cfg.n_schools + 1)],
        "school_level": levels,
        "urbanicity": urban,
    })

    # students
    grade = rng.choice(np.arange(3, 13), size=cfg.n_students)  # grades 3-12
    frpl = rng.random(cfg.n_students) < 0.42
    ell = rng.random(cfg.n_students) < 0.12
    iep = rng.random(cfg.n_students) < 0.14
    gender = rng.choice(["F", "M", "X"], size=cfg.n_students, p=[0.49, 0.49, 0.02])
    race = rng.choice(
        ["White", "Black", "Hispanic", "Asian", "Multi", "Other"],
        size=cfg.n_students,
        p=[0.49, 0.22, 0.17, 0.06, 0.04, 0.02]
    )
    students = pd.DataFrame({
        "student_id": np.arange(2000001, 2000001 + cfg.n_students),
        "birth_year": rng.integers(2007, 2016, cfg.n_students),
        "grade_level": grade,
        "gender": gender,
        "race_ethnicity": race,
        "frpl_flag": frpl.astype(int),
        "ell_flag": ell.astype(int),
        "iep_flag": iep.astype(int),
    })

    # assign students to schools (grade-compatible distribution)
    school_ids = schools["school_id"].values
    # grade-weighted school assignment using level
    level_mask = {
        "elementary": students["grade_level"].between(3, 5).values,
        "middle": students["grade_level"].between(6, 8).values,
        "high": students["grade_level"].between(9, 12).values,
    }
    student_school = np.empty(cfg.n_students, dtype=int)
    for lvl in ["elementary", "middle", "high"]:
        eligible_schools = schools.loc[schools["school_level"] == lvl, "school_id"].values
        idx = np.where(level_mask[lvl])[0]
        student_school[idx] = rng.choice(eligible_schools, size=len(idx))
    students["school_id"] = student_school

    # educators
    role = rng.choice(["teacher", "counselor", "admin"], size=cfg.n_educators, p=[0.83, 0.10, 0.07])
    cert = rng.choice(["standard", "provisional", "none"], size=cfg.n_educators, p=[0.82, 0.14, 0.04])
    years_exp = np.clip(rng.normal(8.5, 6.0, cfg.n_educators).round().astype(int), 0, 35)
    hire_year = (cfg.school_year - years_exp).clip(1995, cfg.school_year)
    educators = pd.DataFrame({
        "educator_id": np.arange(3000001, 3000001 + cfg.n_educators),
        "role": role,
        "certification": cert,
        "years_experience": years_exp,
        "hire_year": hire_year,
    })

    # staffing assignments (school_id x educator_id x year with FTE)
    # each educator assigned to 1-2 schools
    assignments = []
    subject_pool = ["math", "ela", "science", "social_studies", "sped", "counseling", "admin"]
    for _, e in educators.iterrows():
        n_assign = 1 if rng.random() < 0.88 else 2
        schools_for_e = rng.choice(school_ids, size=n_assign, replace=False)
        remaining = 1.0
        for j, sid in enumerate(schools_for_e):
            fte = remaining if j == n_assign - 1 else float(np.round(rng.uniform(0.3, remaining), 2))
            remaining = max(0.0, remaining - fte)
            subj = rng.choice(subject_pool)
            assignments.append({
                "school_id": int(sid),
                "educator_id": int(e["educator_id"]),
                "school_year": cfg.school_year,
                "fte": float(fte),
                "subject_area": subj,
            })
    staffing = pd.DataFrame(assignments)

    # assessments: spring ELA + Math for each student
    # simulate score with subgroup effects + school effect + noise
    school_effect = pd.Series(
        rng.normal(0, 8, cfg.n_schools),
        index=schools["school_id"].values
    )
    base = 250 + (students["grade_level"] - 3) * 7.5
    disadvantage = (
        students["frpl_flag"] * -6.0 +
        students["ell_flag"] * -8.0 +
        students["iep_flag"] * -10.0
    )
    # school effect mapping
    se = students["school_id"].map(school_effect).values
    noise = rng.normal(0, 18, cfg.n_students)
    # subject-specific offsets
    ela_score = base + disadvantage + se + noise + rng.normal(0, 3, cfg.n_students)
    math_score = base + disadvantage + se + noise + rng.normal(0, 3, cfg.n_students)

    def prof_flag(score, grade_level):
        # grade-specific threshold
        thr = 255 + (grade_level - 3) * 6.5
        return (score >= thr).astype(int)

    assessment_rows = []
    for subj, scores in [("ela", ela_score), ("math", math_score)]:
        pf = prof_flag(scores, students["grade_level"].values)
        assessment_rows.append(pd.DataFrame({
            "student_id": students["student_id"].values,
            "school_id": students["school_id"].values,
            "school_year": cfg.school_year,
            "term": "spring",
            "subject": subj,
            "scale_score": np.round(scores, 2),
            "proficient_flag": pf,
        }))
    assessments = pd.concat(assessment_rows, axis=0, ignore_index=True)

    # write raw CSVs
    schools.to_csv(out_dir / "schools.csv", index=False)
    students.drop(columns=["school_id"]).to_csv(out_dir / "students.csv", index=False)
    pd.DataFrame({"student_id": students["student_id"], "school_id": students["school_id"]}).to_csv(out_dir / "student_school.csv", index=False)
    educators.to_csv(out_dir / "educators.csv", index=False)
    staffing.to_csv(out_dir / "staffing.csv", index=False)
    assessments.to_csv(out_dir / "assessments.csv", index=False)
