-- Example relational schema (PostgreSQL-style) for K-16 administrative + assessment data

CREATE TABLE dim_school (
  school_id        INT PRIMARY KEY,
  district_id      INT NOT NULL,
  school_name      TEXT,
  school_level     TEXT, -- elementary/middle/high
  urbanicity       TEXT  -- urban/suburban/rural
);

CREATE TABLE dim_student (
  student_id       BIGINT PRIMARY KEY,
  birth_year       INT,
  grade_level      INT,
  gender           TEXT,
  race_ethnicity   TEXT,
  frpl_flag        BOOLEAN,
  ell_flag         BOOLEAN,
  iep_flag         BOOLEAN
);


CREATE TABLE dim_educator (
  educator_id      BIGINT PRIMARY KEY,
  role             TEXT, -- teacher/counselor/admin
  certification    TEXT,
  years_experience INT,
  hire_year        INT
);

CREATE TABLE fct_staffing (
  school_id        INT REFERENCES dim_school(school_id),
  educator_id      BIGINT REFERENCES dim_educator(educator_id),
  school_year      INT,
  fte              NUMERIC(4,2),
  subject_area     TEXT,
  PRIMARY KEY (school_id, educator_id, school_year)
);

CREATE TABLE fct_assessment (
  student_id       BIGINT REFERENCES dim_student(student_id),
  school_id        INT REFERENCES dim_school(school_id),
  school_year      INT,
  term             TEXT, -- fall/spring
  subject          TEXT, -- math/ela
  scale_score      NUMERIC(7,2),
  proficient_flag  BOOLEAN,
  PRIMARY KEY (student_id, school_id, school_year, term, subject)
);
