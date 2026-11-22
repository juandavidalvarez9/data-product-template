# 2. How input files are checked

- **Date:** 2026-11-22
- **Status:** accepted

## Context

Public data sources change shape without warning: a column is renamed, a date
changes format, a file arrives in another encoding. A pipeline that accepts
whatever it gets turns those changes into wrong numbers that nobody notices.
The sample pipeline must show how to stop early and explain why.

## Decision

1. **A contract per input.** It lists the columns, the type of each one and
   which ones may be empty. The file must have exactly those columns, in any
   order. A missing, repeated or unexpected column stops the run.
2. **Every problem is reported at once.** Whoever fixes the file sees all the
   problems in one run, not one per run. Row checks run only when the header
   is right, because they need the right columns.
3. **The CSV reader does not guess.** The header is read in Python and handed
   to DuckDB as the exact list of columns. When DuckDB was left to detect the
   layout, a file with a short header made it skip the header line without
   any error.
4. **Only comma-separated UTF-8 text.** A byte order mark is accepted. Other
   encodings and separators are rejected with a message that says so, never
   converted by guessing.
5. **Empty means empty or only spaces.** Empty values are written as nulls.
6. **No partial output.** The Parquet file is written under a temporary name
   and renamed at the end, so a failed run leaves the previous output intact.

## Consequences

- A product whose source changes shape fails loudly in CI or in the monthly
  run, with a message that names the problem.
- Error messages with line numbers depend on the wording of DuckDB's errors.
  The tests pin that wording, so an upgrade that changes it fails CI instead
  of producing vague messages.
- A product that needs another separator or encoding converts the file
  first, in its own step, where the conversion can be tested.
