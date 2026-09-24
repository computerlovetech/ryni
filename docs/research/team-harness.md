# Team harness hygiene: practitioner research

Research date: 2026-09-24. Deliverable: [team-harness](../../examples/team-harness/README.md),
an installable pack of deterministic rules only. This is a qualitative synthesis,
not a representative survey or proof that a particular author is a “best” user.
Experienced practice here means concrete workflows, maintenance experience,
examples and tradeoffs, rather than popularity or claims of flawless adherence.

## Source ledger

Each entry records directly read primary material, including discussion text.
No promotional workflow aggregators or search-result snippets serve as evidence.
Relative timestamps in discussion pages are unstable; URLs identify the sources.

| ID | Source | Evidence and dissent |
| --- | --- | --- |
| B1 | Kyle, [Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md), Nov 25 2025 | Keep onboarding focused; route to task details; avoid copying code and using a model as a formatter. A practitioner recommendation, not a universal size experiment. |
| B2 | Shrivu Shankar, [How I Use Every Claude Code Feature](https://blog.sshh.io/p/how-i-use-every-claude-code-feature), with visible comments | Describes a curated 13 KB professional monorepo file, allocating space by cross-team relevance, synchronizing vendor entry points, and learning from agent logs. Comments ask about concurrent edits and warn of malicious skill content. |
| B3 | Shrivu Shankar, [AI Can't Read Your Docs](https://blog.sshh.io/p/ai-cant-read-your-docs), Aug 17 2025 | More documentation cannot compensate for awkward tools; improve help, errors, and local discoverability. This limits what a Markdown linter can solve. |
| H1 | [HN discussion of B1](https://news.ycombinator.com/item?id=46098838) | Replies dispute manual curation versus generated files and whether tuning a changing model is worth the ongoing cost. Other replies defend deterministic formatters and report problematic accumulated memories. |
| H2 | [HN: AGENTS.md outperforms skills in our agent evals](https://news.ycombinator.com/item?id=46809708) | vidarh and OJFord debate context injection versus the decision to invoke a skill. They note the indexed-document comparison does not isolate all mechanisms. Do not infer all skills are inferior. |
| H3 | [HN: Do you still spend time maintaining instruction files?](https://news.ycombinator.com/item?id=48160604) | david_d8912 doubts behavioral compliance; bisonbear advocates team-scale measurement; luodaint distinguishes concrete facts and observed failure fixes from speculative behavior rules. |
| H4 | [HN: Your AGENTS.md file doesn't do anything](https://news.ycombinator.com/item?id=49476140) | Commenters describe environment guidance avoiding wasted setup attempts. LoganDark and Zambyte disagree about whether tool instructions belong in the root or skills. perrygeo prefers a routing index. |
| R1 | [r/ClaudeAI: CLAUDE.md is a super power](https://www.reddit.com/r/ClaudeAI/comments/1mw74t5/claudemd_is_a_super_power/) | Enthusiasm for reusable project context contrasts with Crafty-Wonder-7509 reporting ignored short instructions and complaints about manual updating. Promotional memory-tool replies are weak evidence. |
| R2 | [r/ClaudeCode: What's your setup?](https://www.reddit.com/r/ClaudeCode/comments/1rqo7do/whats_your_claude_code_setup/) | Comments distinguish global personal preferences from project context; describe a compact path table and on-demand reads instead of importing every knowledge file. Many replies promote tools, so treat as workflow examples. |
| R3 | [r/ClaudeCode: Best practices for customizing CLAUDE.md](https://www.reddit.com/r/ClaudeCode/comments/1rigb2s/best_practices_for_customizing_my_claudemd/) | dynoman7 advocates behavior policy, output contracts and memory rules. This conflicts with the “mostly concrete facts” position, so no semantic behavior-style rule is imposed. |
| R4 | [r/codex: What is in your agents.md?](https://www.reddit.com/r/codex/comments/1vdss0w/what_is_in_your_agentsmd_in_codex_app/) | nicky_factz recommends project routing with explicit read conditions and isolated A/B tests; others post extensive behavioral policy. Compression may increase follow-up tool calls rather than reduce total cost. |

The directly visible B2 comments were read, not the entire gated/collapsed thread.
HN and Reddit comment pages were inspected as well as their original posts.
Comment anecdotes are evidence of developer concerns, not verified performance
measurements. The blog sample has two independent authors; B2 and B3 are not two
independent endorsements. This sample emphasizes English-language public agent
users and overrepresents people motivated to share workflows or sell tooling.

## Jobs teams repeatedly need to get done

1. **Start work with the right shared context.** Give a teammate's agent an entry
   point, reliable commands and a route to specialized guidance. B1, H3, H4 and
   R2/R4 support this job. TEAM001–002 check presence and nonempty files; they
   cannot judge whether the commands are correct or the map is sufficient.
2. **Spend context on the current task.** Keep repeated instructions compact;
   put deeper procedures in skills or linked documents. B1/B2 and R2 emphasize
   this, while H2 warns that on-demand activation can fail. TEAM003–004 and
   TEAM014 enforce explicit size policies, not token counts or activation quality.
3. **Keep the guidance map working as code changes.** Broken pointers and merge
   debris are mechanical maintenance failures. TEAM005–008 check reachable local
   references and recursive imports. This is our operational interpretation of
   the progressive-disclosure job, not a claim commenters prescribed these exact
   algorithms. The check is limited to explicit CommonMark links and standalone
   imports; it does not guess whether every path in prose is a reference.
4. **Change a convention once without fragmenting the team.** B2 describes keeping
   tool-specific entry points synchronized. TEAM010–011 catch exact duplicated
   content and inherited repetition. Distinct tool-specific guidance remains
   legitimate; symlinks are an option, not a universal requirement.
5. **Move a workflow between developers and tools.** R1/R2 distinguish personal
   setup and shared project guidance. TEAM009 and TEAM018 catch selected local
   machine dependencies. TEAM012–015 give skills stable metadata and discoverable
   identities. Skill syntax rules are engineering prerequisites; their exact
   limits are explicit pack policy, not conclusions from a popularity poll.
6. **Finish and maintain reusable procedures.** TEAM016–017 detect narrow forms of
   unfinished guidance. B2's log-based improvement loop and H3/R4's demand for
   measurement motivate committing and testing pack changes. Linting complements
   that loop; it does not establish that instructions improve task outcomes.

## Open disagreements and decisions

**How short?** B1 favors very short entry points; B2 reports a much larger useful
professional file. We choose 250 lines AND 16 KiB as a configurable-by-rule-selection
starting convention. No source establishes an optimal cutoff. Skills get a
separate 500-line cap because their job differs from always-loaded instructions.

**Always load or load on demand?** H2 raises the risk that skills are never called.
Do not mechanically move every command out of root context. Keep essential local
setup visible and route specialized detail. The pack checks size and references,
not the relevance of that split.

**Facts or behavior?** H3 favors concrete environment facts and observed regression
prevention; R3 favors reasoning/output policy. Do not lint words such as “always”
or “never,” require an English trigger phrase, or infer contradictory instructions
from matching keywords. Those would produce misleading deterministic findings.

**Human curation or agent maintenance?** H1 contains disagreement. R1 reports both
benefit and failure. Generated content is not automatically bad; reviewed, tested
changes matter. The pack does not ban generators or require a magic filename.

**One document or a hierarchy?** Nested files reduce irrelevant context but add
lookup and inheritance ambiguity. TEAM011 catches only long identical inherited
paragraphs. It does not prescribe a directory taxonomy or flatten monorepos.

**Memory and governance?** The visible B2 discussion raises concurrency and skill
trust questions. These need runtime isolation, provenance and actual controls.
This pack does not certify prompt-injection resistance or infer team ownership
from the mere presence of CODEOWNERS. No review rules were added to cover them.

**Freshness?** File age is not evidence of staleness. Check broken references and
placeholders; avoid arbitrary “updated within 30 days” findings. Tests/CI and
real agent traces should determine whether a guidance change helped.

## Adoption and interpretation

Use the pack as a menu of explicit team conventions. Run on a fixed commit and
look at individual findings before adopting it as a gate. For behavioral changes,
compare representative agent tasks and track success, rework, time and tool calls;
a smaller Markdown file alone is not success. This study benchmarks **Rýni's
checking performance**, not downstream model capability.

The benchmark intentionally includes mature repositories with little or no agent
configuration. TEAM001 findings reflect the opted-in convention and are not
criticisms of those projects. Bare code paths, fragments, site-generated URLs,
semantic contradictions and English prose quality are not silently counted as
validated coverage. See the pack README for exact exclusions.
