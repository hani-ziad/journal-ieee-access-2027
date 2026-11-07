-- Step 2: export every TAWOS project with at least 30 usable sprints.
-- Same three tables and columns as the original eight-project export
-- (week-12-method-preliminary-results/sprint-risk-prediction/scripts/export_tawos_subset.sql),
-- only the project filter changes. Save each result in data/raw/tawos_all/ with
-- exactly these file names:
--   tawos_sprint.csv, tawos_issue.csv, tawos_change_log.csv
-- Export with a header row, comma-separated, UTF-8.

-- Projects that pass the rule (used by all three queries below).
DROP TEMPORARY TABLE IF EXISTS study_projects;
CREATE TEMPORARY TABLE study_projects AS
SELECT s.Project_ID
FROM Sprint s
WHERE s.State = 'CLOSED'
  AND s.Start_Date IS NOT NULL AND s.End_Date IS NOT NULL
  AND s.Complete_Date IS NOT NULL AND s.End_Date >= s.Start_Date
  AND s.Complete_Date >= s.Start_Date
GROUP BY s.Project_ID
HAVING COUNT(*) >= 30;

-- 1) tawos_sprint.csv
SELECT s.ID, s.JiraID, s.Name, s.State, s.Start_Date, s.Activated_Date,
       s.End_Date, s.Complete_Date, TRIM(p.Name) AS Project_Name
FROM Sprint s
JOIN Project p ON p.ID = s.Project_ID
WHERE s.Project_ID IN (SELECT Project_ID FROM study_projects)
ORDER BY TRIM(p.Name), s.Start_Date, s.ID;

-- 2) tawos_issue.csv  (all issues of those projects, including ones with no current sprint)
SELECT i.ID, i.Issue_Key, i.Type, i.Status, i.Story_Point, i.Priority,
       i.Creation_Date, i.Resolution_Date, i.Sprint_ID, i.Assignee_ID,
       TRIM(p.Name) AS Project_Name
FROM Issue i
JOIN Project p ON p.ID = i.Project_ID
WHERE i.Project_ID IN (SELECT Project_ID FROM study_projects)
ORDER BY i.ID;

-- 3) tawos_change_log.csv  (Sprint and Story Points history only)
SELECT c.ID, c.Issue_ID, c.Field, c.From_Value, c.To_Value, c.From_String,
       c.To_String, c.Change_Type, c.Creation_Date, TRIM(p.Name) AS Project_Name
FROM Change_Log c
JOIN Issue i ON i.ID = c.Issue_ID
JOIN Project p ON p.ID = i.Project_ID
WHERE i.Project_ID IN (SELECT Project_ID FROM study_projects)
  AND (LOWER(c.Field) LIKE '%sprint%' OR LOWER(c.Field) LIKE '%story%point%')
ORDER BY c.Issue_ID, c.Creation_Date, c.ID;
