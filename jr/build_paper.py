"""Assemble paper/main.tex from paper/main_body.tex, the theory section and the verified bibliography.

    python -m jr.build_paper

The bibliography is ordered by first citation. Every entry below was checked against Crossref (the DOI
is in the entry) or the publisher's page (JMLR, IJCAI, the journal's index for Holm 1979) on 7 Nov 2026.
"""
from __future__ import annotations

import re

import jr

BIB = {
"choet2018": r"M. Choetkiertikul, H. K. Dam, T. Tran, A. Ghose, and J. Grundy, ``Predicting delivery capability in iterative software development,'' \emph{IEEE Trans. Softw. Eng.}, vol. 44, no. 6, pp. 551--573, Jun. 2018, doi: 10.1109/TSE.2017.2693989.",
"sprint2vec": r"M. Choetkiertikul, P. Banyongrakkul, C. Ragkhitwetsagul, S. Tuarob, H. K. Dam, and T. Sunetnanta, ``Sprint2Vec: A deep characterization of sprints in iterative software development,'' \emph{IEEE Trans. Softw. Eng.}, vol. 51, no. 1, pp. 220--242, Jan. 2025, doi: 10.1109/TSE.2024.3509016.",
"hearty2009": r"P. Hearty, N. Fenton, D. Marquez, and M. Neil, ``Predicting project velocity in XP using a learning dynamic Bayesian network model,'' \emph{IEEE Trans. Softw. Eng.}, vol. 35, no. 1, pp. 124--137, Jan. 2009, doi: 10.1109/TSE.2008.76.",
"perez2024": r"Y. J. P\'erez Castillo, S. D. Orantes Jim\'enez, and P. O. Letelier Torres, ``Sprint management in Agile approach: Progress and velocity evaluation applying machine learning,'' \emph{Information}, vol. 15, no. 11, Art. no. 726, 2024, doi: 10.3390/info15110726.",
"obike2025": r"P. G. Obike, V. E. Ekong, and O. U. Obot, ``A novel scoring-based Agile sprint deliverability prediction and prioritization using machine learning,'' \emph{Int. J. Comput. Appl.}, vol. 187, no. 49, pp. 40--53, 2025, doi: 10.5120/ijca2025925837.",
"kula2022": r"E. Kula, E. Greuter, A. van Deursen, and G. Gousios, ``Factors affecting on-time delivery in large-scale agile software development,'' \emph{IEEE Trans. Softw. Eng.}, vol. 48, no. 9, pp. 3573--3592, Sep. 2022, doi: 10.1109/TSE.2021.3101192.",
"kaufman2012": r"S. Kaufman, S. Rosset, C. Perlich, and O. Stitelman, ``Leakage in data mining: Formulation, detection, and avoidance,'' \emph{ACM Trans. Knowl. Discov. Data}, vol. 6, no. 4, pp. 1--21, 2012, doi: 10.1145/2382577.2382579.",
"kapoor2023": r"S. Kapoor and A. Narayanan, ``Leakage and the reproducibility crisis in machine-learning-based science,'' \emph{Patterns}, vol. 4, no. 9, Art. no. 100804, 2023, doi: 10.1016/j.patter.2023.100804.",
"abusharkh2027": r"H. AbuSharkh, M. Hanif, and R. Damseh, ``Reconstructing sprint-start Jira state for leakage-aware outcome prediction,'' submitted to the IEEE Canadian Conf. Electr. Comput. Eng. (CCECE), 2027.",
"tawos": r"V. Tawosi, A. Al-Subaihin, R. Moussa, and F. Sarro, ``A versatile dataset of agile open source software projects,'' in \emph{Proc. 19th Int. Conf. Mining Softw. Repositories (MSR)}, 2022, pp. 707--711, doi: 10.1145/3524842.3528029.",
"choet2015": r"M. Choetkiertikul, H. K. Dam, T. Tran, and A. Ghose, ``Characterization and prediction of issue-related risks in software projects,'' in \emph{Proc. IEEE/ACM 12th Working Conf. Mining Softw. Repositories (MSR)}, 2015, pp. 280--291, doi: 10.1109/MSR.2015.33.",
"choet2017": r"M. Choetkiertikul, H. K. Dam, T. Tran, and A. Ghose, ``Predicting the delay of issues with due dates in software projects,'' \emph{Empir. Softw. Eng.}, vol. 22, no. 3, pp. 1223--1263, 2017, doi: 10.1007/s10664-016-9496-7.",
"kula2021": r"E. Kula, A. van Deursen, and G. Gousios, ``Modeling team dynamics for the characterization and prediction of delays in user stories,'' in \emph{Proc. 36th IEEE/ACM Int. Conf. Automated Softw. Eng. (ASE)}, 2021, pp. 991--1002, doi: 10.1109/ASE51524.2021.9678939.",
"choet2019": r"M. Choetkiertikul, H. K. Dam, T. Tran, T. Pham, A. Ghose, and T. Menzies, ``A deep learning model for estimating story points,'' \emph{IEEE Trans. Softw. Eng.}, vol. 45, no. 7, pp. 637--656, Jul. 2019, doi: 10.1109/TSE.2018.2792473.",
"porru2016": r"S. Porru, A. Murgia, S. Demeyer, M. Marchesi, and R. Tonelli, ``Estimating story points from issue reports,'' in \emph{Proc. 12th Int. Conf. Predictive Models Data Analytics Softw. Eng. (PROMISE)}, 2016, pp. 1--10, doi: 10.1145/2972958.2972959.",
"fu2023": r"M. Fu and C. Tantithamthavorn, ``GPT2SP: A transformer-based agile story point estimation approach,'' \emph{IEEE Trans. Softw. Eng.}, vol. 49, no. 2, pp. 611--625, Feb. 2023, doi: 10.1109/TSE.2022.3158252.",
"tawosi2023": r"V. Tawosi, R. Moussa, and F. Sarro, ``Agile effort estimation: Have we solved the problem yet? Insights from a replication study,'' \emph{IEEE Trans. Softw. Eng.}, vol. 49, no. 4, pp. 2677--2697, Apr. 2023, doi: 10.1109/TSE.2022.3228739.",
"ortu2015": r"M. Ortu, G. Destefanis, B. Adams, A. Murgia, M. Marchesi, and R. Tonelli, ``The JIRA repository dataset: Understanding social aspects of software development,'' in \emph{Proc. 11th Int. Conf. Predictive Models Data Analytics Softw. Eng. (PROMISE)}, 2015, pp. 1--4, doi: 10.1145/2810146.2810147.",
"montgomery2022": r"L. Montgomery, C. L\"uders, and W. Maalej, ``An alternative issue tracking dataset of public Jira repositories,'' in \emph{Proc. 19th Int. Conf. Mining Softw. Repositories (MSR)}, 2022, pp. 73--77, doi: 10.1145/3524842.3528486.",
"tanti2017": r"C. Tantithamthavorn, S. McIntosh, A. E. Hassan, and K. Matsumoto, ``An empirical comparison of model validation techniques for defect prediction models,'' \emph{IEEE Trans. Softw. Eng.}, vol. 43, no. 1, pp. 1--18, Jan. 2017, doi: 10.1109/TSE.2016.2584050.",
"bangash2020": r"A. A. Bangash, H. Sahar, A. Hindle, and K. Ali, ``On the time-based conclusion stability of cross-project defect prediction models,'' \emph{Empir. Softw. Eng.}, vol. 25, no. 6, pp. 5047--5083, 2020, doi: 10.1007/s10664-020-09878-9.",
"falessi2020": r"D. Falessi, J. Huang, L. Narayana, J. F. Thai, and B. Turhan, ``On the need of preserving order of data when validating within-project defect classifiers,'' \emph{Empir. Softw. Eng.}, vol. 25, no. 6, pp. 4805--4830, 2020, doi: 10.1007/s10664-020-09868-x.",
"jimenez2019": r"M. Jimenez, R. Rwemalika, M. Papadakis, F. Sarro, Y. Le Traon, and M. Harman, ``The importance of accounting for real-world labelling when predicting software vulnerabilities,'' in \emph{Proc. 27th ACM Joint Meeting Eur. Softw. Eng. Conf. Symp. Found. Softw. Eng. (ESEC/FSE)}, 2019, pp. 695--705, doi: 10.1145/3338906.3338941.",
"shepperd2014": r"M. Shepperd, D. Bowes, and T. Hall, ``Researcher bias: The use of machine learning in software defect prediction,'' \emph{IEEE Trans. Softw. Eng.}, vol. 40, no. 6, pp. 603--616, Jun. 2014, doi: 10.1109/TSE.2014.2322358.",
"marquez2018": r"A. E. M\'arquez-Chamorro, M. Resinas, and A. Ruiz-Cort\'es, ``Predictive monitoring of business processes: A survey,'' \emph{IEEE Trans. Serv. Comput.}, vol. 11, no. 6, pp. 962--977, 2018, doi: 10.1109/TSC.2017.2772256.",
"teinemaa2019": r"I. Teinemaa, M. Dumas, M. La Rosa, and F. M. Maggi, ``Outcome-oriented predictive process monitoring: Review and benchmark,'' \emph{ACM Trans. Knowl. Discov. Data}, vol. 13, no. 2, pp. 1--57, 2019, doi: 10.1145/3301300.",
"difrancesco2018": r"C. Di Francescomarino, C. Ghidini, F. M. Maggi, and F. Milani, ``Predictive process monitoring methods: Which one suits me best?'' in \emph{Business Process Management (BPM)}, Lecture Notes in Computer Science, 2018, pp. 462--479, doi: 10.1007/978-3-319-98648-7\_27.",
"fahrenkrog2022": r"S. A. Fahrenkrog-Petersen, N. Tax, I. Teinemaa, M. Dumas, M. de Leoni, F. M. Maggi, and M. Weidlich, ``Fire now, fire later: Alarm-based systems for prescriptive process monitoring,'' \emph{Knowl. Inf. Syst.}, vol. 64, no. 2, pp. 559--587, 2022, doi: 10.1007/s10115-021-01633-w.",
"fawcett2006": r"T. Fawcett, ``An introduction to ROC analysis,'' \emph{Pattern Recognit. Lett.}, vol. 27, no. 8, pp. 861--874, 2006, doi: 10.1016/j.patrec.2005.10.010.",
"hand2009": r"D. J. Hand, ``Measuring classifier performance: A coherent alternative to the area under the ROC curve,'' \emph{Mach. Learn.}, vol. 77, no. 1, pp. 103--123, 2009, doi: 10.1007/s10994-009-5119-5.",
"hernandez2012": r"J. Hern\'andez-Orallo, P. Flach, and C. Ferri, ``A unified view of performance metrics: Translating threshold choice into expected classification loss,'' \emph{J. Mach. Learn. Res.}, vol. 13, no. 91, pp. 2813--2869, 2012.",
"elkan2001": r"C. Elkan, ``The foundations of cost-sensitive learning,'' in \emph{Proc. 17th Int. Joint Conf. Artif. Intell. (IJCAI)}, 2001, pp. 973--978.",
"brier1950": r"G. W. Brier, ``Verification of forecasts expressed in terms of probability,'' \emph{Monthly Weather Rev.}, vol. 78, no. 1, pp. 1--3, 1950, doi: 10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2.",
"vancalster2019": r"B. Van Calster, D. J. McLernon, M. van Smeden, L. Wynants, and E. W. Steyerberg, ``Calibration: The Achilles heel of predictive analytics,'' \emph{BMC Med.}, vol. 17, 2019, doi: 10.1186/s12916-019-1466-7.",
"niculescu2005": r"A. Niculescu-Mizil and R. Caruana, ``Predicting good probabilities with supervised learning,'' in \emph{Proc. 22nd Int. Conf. Mach. Learn. (ICML)}, 2005, pp. 625--632, doi: 10.1145/1102351.1102430.",
"skellam1948": r"J. G. Skellam, ``A probability distribution derived from the binomial distribution by regarding the probability of success as variable between the sets of trials,'' \emph{J. R. Stat. Soc. Ser. B}, vol. 10, no. 2, pp. 257--261, 1948, doi: 10.1111/j.2517-6161.1948.tb00014.x.",
"breiman2001": r"L. Breiman, ``Random forests,'' \emph{Mach. Learn.}, vol. 45, no. 1, pp. 5--32, 2001, doi: 10.1023/A:1010933404324.",
"friedman2001": r"J. H. Friedman, ``Greedy function approximation: A gradient boosting machine,'' \emph{Ann. Statist.}, vol. 29, no. 5, pp. 1189--1232, 2001, doi: 10.1214/aos/1013203451.",
"sklearn": r"F. Pedregosa \emph{et al.}, ``Scikit-learn: Machine learning in Python,'' \emph{J. Mach. Learn. Res.}, vol. 12, no. 85, pp. 2825--2830, 2011.",
"field2007": r"C. A. Field and A. H. Welsh, ``Bootstrapping clustered data,'' \emph{J. R. Stat. Soc. Ser. B}, vol. 69, no. 3, pp. 369--390, 2007, doi: 10.1111/j.1467-9868.2007.00593.x.",
"youden1950": r"W. J. Youden, ``Index for rating diagnostic tests,'' \emph{Cancer}, vol. 3, no. 1, pp. 32--35, 1950, doi: 10.1002/1097-0142(1950)3:1<32::AID-CNCR2820030106>3.0.CO;2-3.",
"tarone1979": r"R. E. Tarone, ``Testing the goodness of fit of the binomial distribution,'' \emph{Biometrika}, vol. 66, no. 3, pp. 585--590, 1979, doi: 10.1093/biomet/66.3.585.",
}
BIB.update({
"vickers2006": r"A. J. Vickers and E. B. Elkin, ``Decision curve analysis: A novel method for evaluating prediction models,'' \emph{Med. Decis. Making}, vol. 26, no. 6, pp. 565--574, 2006, doi: 10.1177/0272989X06295361.",
"holm1979": r"S. Holm, ``A simple sequentially rejective multiple test procedure,'' \emph{Scand. J. Statist.}, vol. 6, no. 2, pp. 65--70, 1979.",
"davis2006": r"J. Davis and M. Goadrich, ``The relationship between precision-recall and ROC curves,'' in \emph{Proc. 23rd Int. Conf. Mach. Learn. (ICML)}, 2006, pp. 233--240, doi: 10.1145/1143844.1143874.",
})


PRE = r"""% Journal draft for IEEE Access, assembled by jr/build_paper.py from main_body.tex. Edit main_body.tex.
% Written in IEEEtran (journal) so it compiles anywhere; move into ieeeaccess.cls (Overleaf) at submission.
% Every number in the text, tables and theory section is a macro generated from the result files by
% jr/tables.py and jr/macros.py; jr/paper_checks.py checks the claims that are not plain numbers.
\documentclass[journal]{IEEEtran}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{cite}
\usepackage{url}
\def\UrlBreaks{\do\/\do-\do.}
\usepackage{graphicx}
\newtheorem{proposition}{Proposition}
\newtheorem{definition}{Definition}
\input{tables/numbers}
\input{tables/textnums}
% \input is not expandable inside tabular in current LaTeX; the primitive is.
\makeatletter\newcommand{\tabinput}[1]{\@@input #1 }\makeatother

\begin{document}

\title{What Predicts Sprint Spillover Without Hindsight? A Benchmark of Feature Families on Public Jira Data}

% Co-authors to be confirmed before submission.
\author{Hani~AbuSharkh%
\thanks{H. AbuSharkh is with the Higher Colleges of Technology, Al Ain, UAE (e-mail: habusharkh@hct.ac.ae).}}

\maketitle

"""


def fmt(e):
    return re.sub(r"doi: (\S+?)\.$", lambda m: "doi: \\url{" + m.group(1).replace("\\_", "_") + "}.", e)


def main():
    paper = jr.ROOT / "paper"
    body = (paper / "main_body.tex").read_text()
    scan = body.replace("\\input{theory}", (paper / "theory.tex").read_text())
    order = []
    for m in re.finditer(r"\\cite\{([^}]*)\}", scan):
        for k in m.group(1).split(","):
            k = k.strip()
            if k not in order:
                order.append(k)
    missing = [k for k in order if k not in BIB]
    assert not missing, missing
    bib = ("\n\\begin{thebibliography}{99}\n\n" + "\n\n".join(f"\\bibitem{{{k}}} {fmt(BIB[k])}" for k in order)
           + "\n\n\\end{thebibliography}\n\n\\end{document}\n")
    (paper / "main.tex").write_text(PRE + body + bib)
    print(len(order), "references; unused:", [k for k in BIB if k not in order])


if __name__ == "__main__":
    main()
