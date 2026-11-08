# Data notice

`tawos_8projects/` (and `tawos_all/`, which is not in git) are extracts of the TAWOS dataset:
V. Tawosi, A. Al-Subaihin, R. Moussa and F. Sarro, "A versatile dataset of agile open source software
projects," MSR 2022, doi:10.1145/3524842.3528029. TAWOS is released under the Apache License 2.0
(https://www.apache.org/licenses/LICENSE-2.0) for research use; please cite it and do not attempt to
re-identify the people in it. The extracts here are unchanged rows of three TAWOS tables, filtered by
project and, for the change log, by field.

`external/` (not in git) holds issues pulled from the public Jira sites of MariaDB and MongoDB. It is not
redistributed. Rebuild it with `data_export/outside/pull_jira_browser.js` (run in the browser on the Jira
site) and `data_export/outside/convert_jira.py`.
