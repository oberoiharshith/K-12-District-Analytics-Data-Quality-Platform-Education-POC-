-- Example policy queries

-- 1) Staffing ratio by school: students per teacher (FTE)
SELECT
  s.school_id,
  s.school_name,
  COUNT(DISTINCT a.student_id) AS n_students,
  SUM(CASE WHEN e.role='teacher' THEN st.fte ELSE 0 END) AS teacher_fte,
  COUNT(DISTINCT a.student_id) / NULLIF(SUM(CASE WHEN e.role='teacher' THEN st.fte ELSE 0 END),0) AS students_per_teacher
FROM dim_school s
JOIN fct_assessment a ON a.school_id = s.school_id AND a.school_year = 2025 AND a.term='spring'
JOIN fct_staffing st ON st.school_id = s.school_id AND st.school_year = 2025
JOIN dim_educator e ON e.educator_id = st.educator_id
GROUP BY 1,2;

-- 2) Proficiency gaps by subgroup (FRPL / ELL / IEP)
SELECT
  subject,
  AVG(CASE WHEN frpl_flag THEN proficient_flag::int END) AS frpl_proficiency,
  AVG(CASE WHEN NOT frpl_flag THEN proficient_flag::int END) AS non_frpl_proficiency
FROM fct_assessment a
JOIN dim_student st ON st.student_id = a.student_id
WHERE a.school_year = 2025 AND a.term='spring'
GROUP BY 1;
