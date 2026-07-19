# scheduler — Test Matrix: Report

Cases for `writers/report.py` (`build_schedule_report` + `HtmlReportWriter`). In `test_report.py`. Status: ☑ covered · ☐ no test yet. The end-to-end golden case is `slow`.

| Case | Expected | Test | Status |
|---|---|---|---|
| Golden rows (Scheduler A solve) | pinned conf/sched/NC ranks, opponents, H2H | `test_schedule_report_rows_for_one_four_team_and_one_five_team_division` | ☑ |
| SOS averages | match recomputed avg of opponents' ranks (overall 1–18 + NC 1–9) | (same test) | ☑ |
| Scheduler display name | "Scheduler A (fixed-rank)" / "Scheduler B (full CP-SAT)" / "Scheduler C (fixed-place + CP-SAT)" | `test_html_report_shows_scheduler_display_name` `[P]` | ☑ |
| Difficulty knobs per scheduler | a/t rows for B, c_spread for C, neither for A | `test_html_report_shows_difficulty_knobs_per_scheduler` | ☑ |
| New SOS columns render | headers + formatted values present | `test_html_report_has_new_columns_and_values` | ☑ |
| Sortable headers | `data-sort` (order/num), row `data-index`, embedded script | `test_html_report_marks_sortable_headers` | ☑ |
