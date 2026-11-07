# Strict review of the draft (7 Nov 2026, second pass)

Done in this pass:

1. **Hypotheses written after a look at 61% of the data.** Added a confirmation set: every hypothesis test repeated on the 21 projects that the development run never saw (Table "confirm"). The in-sprint hypotheses and the serious-spillover results replicate; the spillover part of H1 does not and is now reported as unconfirmed. Logged in PLAN.md as added after the full run.
2. **Thin related work.** 18 to 42 references, in four subsections. Every reference was checked against Crossref (DOI in the entry) or the publisher's page (JMLR, IJCAI); none was typed from memory. Two candidates were dropped because they could not be verified (Usman et al. 2014; Self and Liang 1987).
3. **Light theory.** Added Proposition 3 (overdispersion, beta-binomial variance) with proof, checked by simulation. Turned the binomial model into a predictor with no learning: it comes within 0.03 AUC of gradient boosting, which shows most of the planning-time ranking is one number per team, and its poor calibration is explained by Proposition 3 (estimated intra-sprint correlation 0.18).

All numbers: `python -m jr.paper_checks` (189 checks) and `python -m jr.theory_checks` pass.

Still open:

- The head-to-head uses partial versions of prior feature sets (said plainly in the paper).
- Overlap with the CCECE paper: disclose in the cover letter; run the similarity check.
- No practitioner validation.
- Template (ieeeaccess.cls, author bios and photos) and authorship.
- A comparison table of prior studies (data, labels, timing, validation) would help Section II, but every cell would need checking against the papers themselves; not done.
