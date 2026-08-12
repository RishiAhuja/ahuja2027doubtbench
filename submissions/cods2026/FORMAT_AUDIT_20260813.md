# CODS 2026 format audit

Checked on 2026-08-13 against:

- CODS 2026 common instructions: <https://ikdd.acm.org/cods-2026/common-instructions-and-policies.php>
- CODS 2026 main-track call: <https://ikdd.acm.org/cods-2026/call-for-main-track-papers.php>
- Official ACM Overleaf template: <https://www.overleaf.com/latex/templates/acm-conference-proceedings-primary-article-template/wbvnghjbzwpc>
- Production `acmart` release mirrored by CTAN: <https://ctan.org/pkg/acmart>

## Result

The manuscript matches the CODS 2026 archival-paper format.

| Requirement | Manuscript | Verdict |
|---|---|---|
| ACM proceedings style | `\documentclass[sigconf]{acmart}` | Pass |
| Current template | `acmart` 2.19, dated 2026-06-27 | Pass |
| Bibliography | `ACM-Reference-Format` | Pass |
| Paper size and layout | US letter, two-column `sigconf` | Pass |
| Main-track archival length | 8 content pages plus references, 9 pages total | Pass |
| Double anonymity | Anonymous title block; no affiliations, acknowledgments, or funding; no author PDF metadata | Pass |
| Overleaf primary file | `sample-sigconf.tex` | Pass |
| Clean upload build | ZIP compiles with pdfLaTeX and BibTeX without external project files | Pass |

References begin on page 8 after the conclusion and continue through page 9.
This remains within the stated limit of eight content pages plus up to two
reference pages.

The submission source retains review-stage conference/copyright placeholders.
Final DOI, ISBN, rights, author, affiliation, acknowledgment, and funding data
must be inserted only after acceptance using the values supplied by ACM.

## Files

- Downloaded production template archive: `template_current_20260813/acmart-ctan.zip`
- Overleaf-ready package: `doubtbench-cods2026-overleaf.zip`
- Verified PDF: `paper/main.pdf`

