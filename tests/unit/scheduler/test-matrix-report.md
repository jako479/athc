# scheduler — Test Matrix: Report

Cases for `writers/report.py` (`build_schedule_report` + `HtmlReportWriter`). In `test_report.py`. Status: ☑ covered · ☐ no test yet. The row test reads the shared solved schedule of every league case and is `slow`.

| Case | Expected | Test | Status |
|---|---|---|---|
| Rows match recomputed SOS (every league case) | ranks + SOS fields recomputed independently (`validate_report`) | `test_schedule_report_rows_match_recomputed_sos` | ☑ |
| Scheduler description | "two-phase CP-SAT" | `test_html_report_shows_scheduler_description` | ☑ |
| Title carries the league name | `<name> Schedule Report` in title and heading | `test_html_report_title_carries_the_league_name` | ☑ |
| CPU, threads and seed | shows the CPU name, solver thread count and seed | `test_html_report_shows_cpu_threads_and_seed` | ☑ |
| Difficulty knob | shows Difficulty spread | `test_html_report_shows_difficulty_knob` | ☑ |
| Columns render (Conf Rank after Avg NC SOS 1-18) | headers, order, formatted values | `test_html_report_has_new_columns_and_values` | ☑ |
| Sortable headers | `data-sort` (order/num), row `data-index`, embedded script | `test_html_report_marks_sortable_headers` | ☑ |
