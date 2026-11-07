# Quick strict review of the first full draft (7 Nov 2026)

Fixed in this pass: every number in the running text is checked against the result files (`python -m jr.paper_checks`, 130 checks) and every table and theory number is generated (`python -m jr.tables`), so nothing is typed by hand. Removed claims the data do not support (that the new features help "mainly" through two of them; that seriously late is ranked better than late closure; that no earlier study reconstructs features to prediction time). Credited the Youden cost-ratio link to the ROC literature instead of presenting it as new. Added the figure of all 22 hypothesis comparisons. Rewrote in plain, short sentences with no dashes.

What a strict IEEE Access reviewer will still raise, most serious first:

1. **Hypotheses written after seeing 61% of the data.** The eight development projects hold 2,602 of the 4,235 sprints. The paper says so in Threats; a reviewer may still discount the "pre-stated" framing. Do not oversell it in the cover letter.
2. **Related work is thin (18 references).** IEEE Access papers usually cite 30 to 50. Needs a proper literature pass on iteration and sprint prediction, Jira mining, and time-aware validation in software analytics. Every new reference must be checked against the source.
3. **The head-to-head uses partial versions of prior work.** Worki-style features are our reading of their verbal definitions; the Choetkiertikul set lacks their team and issue features. The paper says it measures families, not papers, but expect a reviewer to call the comparison unfair to them.
4. **"Theory" is light.** Proposition 1 is the law of total probability and Proposition 2 is a known link. Their value is that they predict and explain results, which the paper now says plainly. A reviewer wanting deep theory will not find it.
5. **Overlap with the CCECE paper.** Same reconstruction, same first author. Disclose in the cover letter and keep the reconstruction section short, as it is now. Run the similarity check before submitting.
6. **No practitioner validation.** Nobody has confirmed that the flagged sprints are the ones a Scrum Master would want to hear about. Stated as the next step; a short rating study would make the paper much stronger.
7. **Format.** The draft is in IEEEtran so it compiles anywhere. IEEE Access needs its own template (ieeeaccess.cls on Overleaf), author biographies and photos. `main_preview.pdf` is a local preview, not the final layout.
8. **Authorship.** Decide whether the CCECE co-authors are on this paper; the reconstruction is shared work.
