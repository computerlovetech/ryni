# Structured output and fixes

```sh
ryni check . --output-format json
```

JSON output contains exactly one object on stdout, including for configuration
or input errors. Argument-parsing errors are handled by Clap on stderr before a
scan starts. There is no ANSI color or human summary in JSON output.

The schema has `schema_version = 1` and these fields:

| Field | Meaning |
| --- | --- |
| `complete` | False when any execution error prevented a complete scan. Lint findings alone do not make a scan incomplete. |
| `files_discovered` | Supported files admitted by discovery. |
| `files_checked` | Files successfully read and analyzed; individual target errors can still make the scan incomplete. |
| `files_fixed` | Files changed during this invocation. Findings describe the subsequent check. |
| `diagnostics` | Sorted findings with `rule`, `severity`, `message`, `path`, `range`, `location`, `end_location`, and `fix`. |
| `errors` | Execution failures with `operation`, `path`, and `message`. |

Paths use forward slashes and are normally scan-root-relative for document
findings. Startup/configuration/discovery errors can contain absolute paths.
Non-UTF-8 paths are rendered lossily. Project-level findings use `.` as their path.
All current findings have severity `error`.

`range` is null for a file-level finding, otherwise `{ "start": 0, "end": 10 }`
with half-open UTF-8 byte offsets. Locations are null or objects containing
one-based `line` and Unicode scalar `column`. End locations are exclusive.
Consumers must not interpret columns as bytes, terminal display cells or UTF-16
code units. Human messages may change; use the stable rule ID for automation.

A proposed fix has `title`, `applicability` (`safe`, `unsafe` or `display-only`),
and `edits`. Each edit has a byte `range` and `replacement` string. A proposal does
not mean the file has been changed. Schema consumers should tolerate additional
object fields. Incompatible structural changes will increment the schema version.

Exit codes remain `0` for clean/empty scans, `1` for findings, and `2` for execution
errors. Execution errors take precedence over findings. Phase timing output is
opt-in on stderr and is not part of this JSON contract.

## Applying fixes

```sh
ryni check . --fix
ryni check . --fix --unsafe-fixes
```

`--fix` applies only safe fixes. The first implemented fix is for
`skill-directory-name`; it is **unsafe**, so it requires both flags. It sets the
skill name to a valid containing-directory name and reserializes its frontmatter.
This changes the skill identity and may remove YAML comments or alter formatting.
The document body, BOM, and existing CRLF style are preserved. No safe fixes are
currently offered by built-in rules. Display-only fixes are never applied.

Fixes are skipped for incomplete scans. For each affected file, Ryni verifies
that its contents still match the analyzed snapshot, validates edit ranges,
rejects overlapping edits, and checks that the resulting skill frontmatter
parses. It writes through a temporary file, preserves permissions and replaces
the destination. Individual files are replaced atomically; the whole repository
is not one transaction. Avoid editing files concurrently with fix application.

Changed files are rechecked before output is produced. Remaining findings still
cause exit code `1`; application or recheck errors cause exit code `2`.
