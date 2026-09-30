# Rýni documentation

<div class="ryni-intro" markdown>

A harness linter, written in Rust.

Harness engineering is hard. Keeping a team aligned on it is harder. Ryni checks
your Markdown links and Agent Skills metadata, so your coding agents can rely on
the instructions and skills your team maintains.

[Install ryni →](installation.md){ .md-button .md-button--primary }
[Explore the rules](rules.md){ .ryni-secondary-link }

</div>

## Find your next step

<div class="grid cards" markdown>

-   **Check your harness**

    Run checks locally or in CI, read diagnostics, and understand which files
    ryni scans.

    [CLI usage →](usage.md)

-   **Understand the rules**

    See what each built-in rule checks, with the supported standards and their
    limits.

    [Built-in rules →](rules.md)

</div>

## Start checking

After [installing ryni](installation.md), run it from your project directory:

```sh
ryni check .
```

No configuration is required. Ryni runs locally, needs no model or API key, and
never edits your files. Written in Rust and distributed as a standalone binary,
it requires neither Rust nor Python to run.

## Team rule packs

**Coming soon:** define your team's conventions once and share them across
repositories. Today, ryni runs its built-in rules.

## About the name

[Rýni](https://en.wiktionary.org/wiki/r%C3%BDni#Etymology) comes from Old Norse,
meaning “scrutiny” or “contemplation.”
