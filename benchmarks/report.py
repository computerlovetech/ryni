# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib==3.10.8"]
# ///
"""Create a shareable report and figures from a completed benchmark run."""

import argparse
from collections import Counter
import html
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent
RULES = (
    "markdown-local-link", "skill-frontmatter", "skill-name",
    "skill-directory-name", "skill-description", "skill-optional-fields",
)
BACKGROUND = "#101922"
FOREGROUND = "#eef3f6"
MUTED = "#a7b8c6"
TEAL = "#66e0cb"
CORAL = "#ffad8c"


def summarize(report, manifest):
    if not report["repos"]:
        raise ValueError("The report has no repositories")
    catalog = {repo["name"]: repo for repo in manifest}
    rows = []
    rules = Counter({rule: 0 for rule in RULES})
    for name, result in report["repos"].items():
        if result["status"] != "ok":
            raise ValueError(f"{name}: cannot publish an incomplete or failed scan")
        if name not in catalog or result["revision"] != catalog[name]["revision"]:
            raise ValueError(f"{name}: manifest does not match the scanned revision")
        if sum(result["rules"].values()) != result["findings"]:
            raise ValueError(f"{name}: finding counts do not add up")
        if not 0 <= result["skill_files"] <= result["markdown_files"]:
            raise ValueError(f"{name}: invalid file counts")
        if not result["seconds"] or len(result["seconds"]) != report["repeat"]:
            raise ValueError(f"{name}: incomplete timing samples")
        rows.append({**catalog[name], **result,
                     "median_ms": statistics.median(result["seconds"]) * 1000})
        rules.update(result["rules"])
    return rows, {
        "repositories": len(rows), "languages": len({row["language"] for row in rows}),
        "markdown_files": sum(row["markdown_files"] for row in rows),
        "skill_files": sum(row["skill_files"] for row in rows),
        "findings": sum(row["findings"] for row in rows),
        "repos_with_findings": sum(row["findings"] > 0 for row in rows),
        "repos_with_skills": sum(row["skill_files"] > 0 for row in rows),
        "rules": dict(rules),
    }


def figures(rows, totals, report, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 12,
        "figure.facecolor": BACKGROUND, "axes.facecolor": BACKGROUND,
        "text.color": FOREGROUND, "axes.labelcolor": MUTED,
        "xtick.color": MUTED, "ytick.color": FOREGROUND,
        "axes.edgecolor": BACKGROUND, "svg.fonttype": "none",
    })
    date = report["created_at"][:10]

    def frame(title, subtitle, height=9):
        figure = plt.figure(figsize=(16, height), dpi=100)
        figure.text(.05, .95, "RÝNI  /  FIELD NOTES", color=TEAL, fontsize=13, weight="bold")
        figure.text(.05, .885, title, fontsize=29, weight="bold")
        figure.text(.05, .84, subtitle, fontsize=13, color=MUTED)
        figure.text(.05, .035, f"{date} · Pinned repository snapshots · ryni check .", fontsize=10, color=MUTED)
        figure.text(.95, .035, "github.com/computerlovetech/ryni", ha="right", fontsize=10, color=TEAL)
        return figure

    def save(figure, name):
        for extension in ("png", "svg"):
            figure.savefig(output / f"{name}.{extension}", dpi=100)
        plt.close(figure)

    def axis_style(axis, label):
        axis.set_axisbelow(True)
        axis.grid(axis="x", color="#293743", linewidth=.8)
        axis.set_xlabel(label, labelpad=10)
        axis.tick_params(axis="both", length=0, pad=8)
        axis.xaxis.set_major_locator(MaxNLocator(integer=True))
        for spine in axis.spines.values():
            spine.set_visible(False)

    figure = frame("What does your agent read?", "A real-repository benchmark for Markdown links and Agent Skills metadata.")
    metrics = [
        (totals["repositories"], "open-source repositories"),
        (totals["markdown_files"], "Markdown files scanned"),
        (totals["skill_files"], "SKILL.md files included"),
    ]
    for position, (value, label) in zip((.05, .37, .69), metrics):
        figure.text(position, .655, f"{value:,}", fontsize=61, weight="bold", color=TEAL)
        figure.text(position, .60, label, fontsize=16)
    figure.text(.05, .445, f"{totals['findings']:,} findings to investigate", fontsize=35, weight="bold")
    figure.text(.05, .385,
                f"Across {totals['repos_with_findings']} of {totals['repositories']} repositories · "
                f"{totals['languages']} source-language ecosystems", fontsize=19, color=MUTED)
    active = [(rule, count) for rule, count in totals["rules"].items() if count]
    figure.text(.05, .29, "  /  ".join(f"{count:,} {rule}" for rule, count in active), fontsize=16, color=CORAL, wrap=True)
    figure.text(.05, .16, "Findings ≠ confirmed defects. Generated docs and documentation-specific links can be flagged.", fontsize=13, color=MUTED)
    figure.text(.05, .115, "Skills are a subset of Markdown files. Pinned corpus; no upstream builds or submodule downloads.", fontsize=12, color=MUTED)
    save(figure, "overview")

    ordered = sorted(rows, key=lambda row: row["findings"], reverse=True)
    figure = frame("Coverage & findings, repository by repository", "Counts from the same pinned checkouts. Zero means no findings from the current rules.", height=11)
    coverage = figure.add_axes((.17, .20, .32, .55))
    findings = figure.add_axes((.60, .20, .32, .55))
    positions = list(range(len(ordered)))
    markdown = [row["markdown_files"] for row in ordered]
    skills = [row["skill_files"] for row in ordered]
    coverage.barh(positions, markdown, color="#345966", height=.65)
    coverage.barh(positions, skills, color=TEAL, height=.65)
    coverage.set_yticks(positions, [row["name"] for row in ordered])
    findings.set_yticks(positions, [""] * len(ordered))
    link_counts = [row["rules"].get("markdown-local-link", 0) for row in ordered]
    other_counts = [row["findings"] - count for row, count in zip(ordered, link_counts)]
    findings.barh(positions, link_counts, color=CORAL, height=.65)
    findings.barh(positions, other_counts, left=link_counts, color=TEAL, height=.65)
    for position, row in enumerate(ordered):
        coverage.text(row["markdown_files"] + max(markdown) * .02, position,
                      f"{row['markdown_files']:,} / {row['skill_files']}", va="center", fontsize=10)
        findings.text(row["findings"] + max(totals["findings"], 1) * .006, position,
                      f"{row['findings']:,}", va="center", fontsize=11)
    for axis in (coverage, findings):
        axis.invert_yaxis()
    coverage.set_xlim(0, max(max(markdown), 1) * 1.30)
    findings.set_xlim(0, max(max(row["findings"] for row in ordered), 1) * 1.15)
    coverage.set_title("Markdown / included skills", loc="left", color=FOREGROUND, pad=18)
    findings.set_title("Local links + other rule findings", loc="left", color=FOREGROUND, pad=18)
    axis_style(coverage, "Files · teal = SKILL.md subset")
    axis_style(findings, "Findings · coral = local links; teal = other rules")
    figure.text(.05, .105, "Findings can include generated targets and documentation-specific references; this is not a repository quality ranking.", fontsize=12, color=MUTED)
    save(figure, "repositories")

    ordered = sorted(rows, key=lambda row: row["median_ms"], reverse=True)
    figure = frame("How long does a repository scan take?", f"Median of {report['repeat']} sequential scans per repository; lines show observed minimum–maximum.", height=11)
    axis = figure.add_axes((.17, .22, .72, .54))
    for position, row in enumerate(ordered):
        minimum, maximum = min(row["seconds"]) * 1000, max(row["seconds"]) * 1000
        axis.plot([minimum, maximum], [position, position], color="#51717f", linewidth=4)
        axis.scatter(row["median_ms"], position, s=65, color=TEAL, zorder=3)
        axis.annotate(f"{row['median_ms']:.1f} ms", (maximum, position), xytext=(10, 0),
                      textcoords="offset points", va="center", fontsize=11)
    axis.set_yticks(range(len(ordered)), [row["name"] for row in ordered])
    axis.invert_yaxis()
    axis.set_xlim(0, max(max(row["seconds"]) for row in ordered) * 1250)
    axis_style(axis, "Wall time per CLI invocation (milliseconds)")
    figure.text(.05, .13, f"Host: {report['platform']}", color=MUTED, fontsize=11)
    figure.text(.05, .095, "Includes startup, directory traversal and output capture. No cache flushing or warmup; informational, not a cross-tool comparison.", color=MUTED, fontsize=11)
    save(figure, "timings")


def write_html(rows, totals, report, output):
    escape = html.escape
    rules = list(totals["rules"])
    headers = ["Repository", "Language", "Markdown", "Skills", "Findings", "Median ms", *rules, "Commit"]
    table_rows = []
    for row in sorted(rows, key=lambda row: row["findings"], reverse=True):
        url = row["url"].removesuffix(".git") + "/tree/" + row["revision"]
        cells = [row["name"], row["language"], row["markdown_files"], row["skill_files"],
                 row["findings"], f"{row['median_ms']:.1f}",
                 *[row["rules"].get(rule, 0) for rule in rules]]
        table_rows.append("<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in cells)
                          + f'<td><a href="{escape(url, quote=True)}">{row["revision"][:10]}</a></td></tr>')
    rule_list = "".join(f"<li><code>{escape(rule)}</code>: <strong>{count:,}</strong></li>" for rule, count in totals["rules"].items())
    caption = (f"We ran Rýni across {totals['repositories']} pinned open-source repositories spanning "
               f"{totals['languages']} language ecosystems: {totals['markdown_files']:,} Markdown files, "
               f"including {totals['skill_files']} Agent Skills. It surfaced {totals['findings']:,} findings "
               f"across {totals['repos_with_findings']} repositories. These are review candidates, not confirmed "
               "defects: generated docs and documentation-specific links can trigger findings. "
               "Try it on your harness: ryni check .")
    page = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rýni — repository benchmark</title>
<style>
:root {{color-scheme:dark}} body {{margin:0;background:{BACKGROUND};color:{FOREGROUND};font:16px/1.6 system-ui,sans-serif}}
main {{max-width:1200px;margin:auto;padding:48px 24px}} h1 {{font-size:44px;line-height:1.1}} h2 {{margin-top:48px}}
a {{color:{TEAL}}} p,li {{max-width:950px}} .muted {{color:{MUTED}}} img {{width:100%;height:auto;border-radius:12px}}
.table {{overflow-x:auto}} table {{border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}}
th,td {{padding:10px 14px;border-bottom:1px solid #34505d;text-align:right;white-space:nowrap}}
th:first-child,td:first-child,td:nth-child(2) {{text-align:left}} th {{color:{TEAL}}}
code {{color:{CORAL}}} blockquote {{margin:0;padding:24px;border-left:3px solid {TEAL};background:#172630}}
</style><main>
<p class="muted">RÝNI / FIELD NOTES · {escape(report['created_at'][:10])}</p>
<h1>Inspect the harness.<br>See what needs attention.</h1>
<p>{totals['repositories']} pinned repositories · {totals['languages']} source-language ecosystems ·
{totals['markdown_files']:,} Markdown files · {totals['skill_files']} skills (included in Markdown).</p>
<img src="overview.png" alt="{escape(caption, quote=True)}">
<p><a href="overview.png">Download PNG</a> · <a href="overview.svg">Download SVG</a></p>
<h2>Every repository, every rule</h2>
<p>Skills occur in {totals['repos_with_skills']} repositories. All counts are per scan, not summed across repeated runs.
Findings count diagnostics, not unique files or unique targets. Zero findings does not establish correctness.</p>
<div class="table"><table><thead><tr>{''.join(f'<th scope="col">{escape(header)}</th>' for header in headers)}</tr></thead>
<tbody>{''.join(table_rows)}</tbody></table></div>
<h2>Rule totals</h2><ul>{rule_list}</ul>
<img src="repositories.png" alt="Markdown files, included skills and findings by repository; exact values are in the table.">
<p><a href="repositories.png">Download PNG</a> · <a href="repositories.svg">Download SVG</a></p>
<h2>Performance, with context</h2>
<img src="timings.png" alt="Per-repository median scan time with observed minimum and maximum across repetitions.">
<p><a href="timings.png">Download PNG</a> · <a href="timings.svg">Download SVG</a></p>
<h2>What this tells us</h2>
<p>Rýni can inspect Markdown and Agent Skills across varied repository layouts with a single command.
The corpus reveals links that do not resolve in these checkouts and metadata that violates its current rules.
Generated Rails documentation links and Elixir API-reference syntax illustrate why findings need context.
These observations do not measure precision, recall, or repository quality.</p>
<p>Only Markdown and SKILL.md metadata are checked. Source languages describe the corpus, not language-specific analysis.
Submodules, LFS assets and upstream builds are excluded. The sample is selected, not representative of all open source.</p>
<h2>Method & provenance</h2>
<p>{report['repeat']} sequential CLI invocations per repository; median wall time with observed min–max.
Startup, traversal and captured output are included. No explicit warmup or cache flushing.
Timings are specific to this host and run; cloning and inventory counting are excluded.</p>
<p class="muted">Host: {escape(report['platform'])}<br>Run: {escape(report['created_at'])}<br>
Binary SHA-256: <code>{escape(report['binary_sha256'])}</code></p>
<p><a href="data.json">Full source data and pinned manifest</a> · <a href="https://github.com/computerlovetech/ryni">Rýni on GitHub</a></p>
<h2>Suggested sharing caption</h2><blockquote>{escape(caption)}</blockquote>
</main></html>"""
    (output / "index.html").write_text(page, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, nargs="?", default=ROOT / "results/latest.json")
    parser.add_argument("--manifest", type=Path, default=ROOT / "repos.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results/share")
    args = parser.parse_args()
    report = json.loads(args.input.read_text())
    manifest = json.loads(args.manifest.read_text())
    rows, totals = summarize(report, manifest)
    args.output.mkdir(parents=True, exist_ok=True)
    figures(rows, totals, report, args.output)
    write_html(rows, totals, report, args.output)
    (args.output / "data.json").write_text(json.dumps({"report": report, "manifest": manifest, "totals": totals}, indent=2) + "\n")
    print(f"Report: {args.output / 'index.html'}")
    print(f"{totals['repositories']} repositories, {totals['markdown_files']:,} Markdown files, "
          f"{totals['skill_files']} skills, {totals['findings']:,} findings")


if __name__ == "__main__":
    main()
