# Rýni

**A harness linter, written in Rust.**

Harness engineering is hard. Keeping a team aligned on it is harder. Your coding
agents depend on instructions, skills, and Markdown docs that stay consistent as
projects change. Ryni catches broken local links and invalid Agent Skills
metadata before they get in the way.

- **Check your harness.** Built-in checks for Markdown links and Agent Skills.
- **Run anywhere.** Written in Rust, distributed as a standalone binary.
- **Start immediately.** Run `ryni check .`. No configuration required.

**Team rule packs are coming soon:** define your team's conventions once and
share them across repositories. Today, ryni runs its built-in rules.

## Get started

[Install ryni](installation.md), then run it from your project directory:

```sh
ryni check .
```

Ryni checks local Markdown links and [Agent Skills](https://agentskills.io/specification)
metadata. It runs locally, requires no model or API key, and never edits your files.

- [Installation](installation.md): install, update, or pin a version.
- [CLI usage](usage.md): scanning, diagnostics, and CI.
- [Built-in rules](rules.md): what each rule checks and its limits.

---

*[Rýni](https://en.wiktionary.org/wiki/r%C3%BDni#Etymology) — from Old Norse,
“scrutiny” or “contemplation.”*
