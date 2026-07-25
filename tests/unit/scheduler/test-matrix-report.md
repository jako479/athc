# scheduler — Test Matrix: Report

Cases for `writers/report.py` (`build_schedule_report` + `HtmlReportWriter`). In `test_report.py`. Status: ☑ covered · ☐ no test yet. The end-to-end golden case is `slow`.

| Case | Expected | Test | Status |
|---|---|---|---|
| Rows match recomputed SOS | ranks + SOS fields recomputed independently | `test_schedule_report_rows_match_recomputed_sos` | ☑ |
| SOS averages | match recomputed avg of opponents' ranks (overall 1–18 + NC 1–9) | (same test) | ☑ |
| Scheduler description | "fixed-place + CP-SAT" | `test_html_report_shows_scheduler_description` | ☑ |
| Difficulty knob | shows Difficulty spread | `test_html_report_shows_difficulty_knob` | ☑ |
| Columns render: Team, Overall Rank, Sched Rank, ... (Conf Rank after Avg NC SOS 1-18) | headers, order, formatted values | `test_html_report_has_new_columns_and_values` | ☑ |
| Sortable headers | `data-sort` (order/num), row `data-index`, embedded script | `test_html_report_marks_sortable_headers` | ☑ |
