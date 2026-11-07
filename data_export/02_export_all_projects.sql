-- Step 2: export every TAWOS project with at least 30 usable sprints.
-- Same three tables and columns as the original eight-project export, only the
-- project filter changes. Written server-side with SELECT ... INTO OUTFILE into
-- MySQL's secure_file_priv folder (on a default Windows install:
-- C:\ProgramData\MySQL\MySQL Server 8.0\Uploads\; check with
-- SHOW VARIABLES LIKE 'secure_file_priv'). Then move the three files to
-- data/raw/tawos_all/ as tawos_sprint.csv, tawos_issue.csv, tawos_change_log.csv.
-- NULL is written as the word NULL, as in the eight-project export.
--
-- Three MongoDB projects (MongoDB Compass, the C++ driver, the Java driver) are
-- excluded because the same projects are in the outside test set pulled from
-- MongoDB's live Jira (PLAN.md deviations log, 7 Nov 2026).
-- Two custom fields are dropped from the change log: 'Actual Story Points'
-- (Spring XD, recorded after the work) and 'Story Points (Obsolete)' (Moodle).
-- Neither is the estimate field, and the loader would otherwise read both as
-- story-point history.

DROP TEMPORARY TABLE IF EXISTS study_projects;
CREATE TEMPORARY TABLE study_projects AS
SELECT s.Project_ID
FROM tawos.sprint s
JOIN tawos.project p ON p.ID = s.Project_ID
WHERE s.State = 'CLOSED'
  AND s.Start_Date IS NOT NULL AND s.End_Date IS NOT NULL
  AND s.Complete_Date IS NOT NULL AND s.End_Date >= s.Start_Date
  AND s.Complete_Date >= s.Start_Date
  AND TRIM(p.Name) NOT IN ('MongoDB Compass', 'The Mongo C++ driver', 'The Mongo Java driver')
GROUP BY s.Project_ID
HAVING COUNT(*) >= 30;

-- 1) tawos_sprint.csv
(SELECT 'ID','JiraID','Name','State','Start_Date','Activated_Date','End_Date','Complete_Date','Project_Name')
UNION ALL
(SELECT s.ID, s.JiraID, REPLACE(s.Name, '"', '""'), s.State, s.Start_Date, s.Activated_Date,
        s.End_Date, s.Complete_Date, TRIM(p.Name)
 FROM tawos.sprint s
 JOIN tawos.project p ON p.ID = s.Project_ID
 WHERE s.Project_ID IN (SELECT Project_ID FROM study_projects)
 ORDER BY TRIM(p.Name), s.Start_Date, s.ID
 LIMIT 18446744073709551615)
INTO OUTFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/tawos_all_sprint.csv'
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n';

-- 2) tawos_issue.csv  (all issues of those projects, including ones with no current sprint)
(SELECT 'ID','Issue_Key','Type','Status','Story_Point','Priority','Creation_Date','Resolution_Date','Sprint_ID','Assignee_ID','Project_Name')
UNION ALL
(SELECT i.ID, i.Issue_Key, REPLACE(i.Type, '"', '""'), REPLACE(i.Status, '"', '""'), i.Story_Point,
        REPLACE(i.Priority, '"', '""'), i.Creation_Date, i.Resolution_Date, i.Sprint_ID, i.Assignee_ID,
        TRIM(p.Name)
 FROM tawos.issue i
 JOIN tawos.project p ON p.ID = i.Project_ID
 WHERE i.Project_ID IN (SELECT Project_ID FROM study_projects)
 ORDER BY i.ID
 LIMIT 18446744073709551615)
INTO OUTFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/tawos_all_issue.csv'
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n';

-- 3) tawos_change_log.csv  (Sprint and Story Points history only)
(SELECT 'ID','Issue_ID','Field','From_Value','To_Value','From_String','To_String','Change_Type','Creation_Date','Project_Name')
UNION ALL
(SELECT c.ID, c.Issue_ID, REPLACE(c.Field, '"', '""'),
        REPLACE(REPLACE(REPLACE(c.From_Value, '"', '""'), '\r', ' '), '\n', ' '),
        REPLACE(REPLACE(REPLACE(c.To_Value, '"', '""'), '\r', ' '), '\n', ' '),
        REPLACE(REPLACE(REPLACE(c.From_String, '"', '""'), '\r', ' '), '\n', ' '),
        REPLACE(REPLACE(REPLACE(c.To_String, '"', '""'), '\r', ' '), '\n', ' '),
        c.Change_Type, c.Creation_Date, TRIM(p.Name)
 FROM tawos.change_log c
 JOIN tawos.issue i ON i.ID = c.Issue_ID
 JOIN tawos.project p ON p.ID = i.Project_ID
 WHERE i.Project_ID IN (SELECT Project_ID FROM study_projects)
   AND (LOWER(c.Field) LIKE '%sprint%' OR LOWER(c.Field) LIKE '%story%point%')
   AND c.Field NOT IN ('Actual Story Points', 'Story Points (Obsolete)')
 ORDER BY c.Issue_ID, c.Creation_Date, c.ID
 LIMIT 18446744073709551615)
INTO OUTFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/tawos_all_change_log.csv'
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n';
