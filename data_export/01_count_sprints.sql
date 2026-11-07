-- Step 1: how many usable sprints does each TAWOS project have?
-- Run in MySQL Workbench on the TAWOS database and save the result as
-- data_export/tawos_sprint_counts.csv. Nothing else is needed for this step.
--
-- "Usable" is exactly the Phase 1 loader rule (src/data/load_tawos.py):
-- CLOSED, all three dates present, End_Date and Complete_Date not before Start_Date.
-- The Python code applies the final cut (at least 30 such sprints, minus the
-- first sprint of each project as a cold start).

SELECT
    TRIM(p.Name) AS Project_Name,
    COUNT(*) AS all_sprints,
    SUM(s.State = 'CLOSED') AS closed_sprints,
    SUM(s.State = 'CLOSED'
        AND s.Start_Date IS NOT NULL
        AND s.End_Date IS NOT NULL
        AND s.Complete_Date IS NOT NULL
        AND s.End_Date >= s.Start_Date
        AND s.Complete_Date >= s.Start_Date) AS usable_sprints
FROM Sprint s
JOIN Project p ON p.ID = s.Project_ID
GROUP BY TRIM(p.Name)
ORDER BY usable_sprints DESC;
