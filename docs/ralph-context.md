> **Author's note (February 2026):** This document was written when I believed Ralph loops had been fully absorbed into native agent tooling and were no longer needed as a standalone technique. That assessment was premature. Claude Code's task mode, subagents, and compaction still suffer from context bloat, and the community consensus as of February 2026 is that bash-orchestrated loops with fresh context per iteration remain superior for autonomous multi-task work. See [we-still-need-ralph-at-least-with-claude.md](we-still-need-ralph-at-least-with-claude.md) for the full analysis. The sections below marked with ⚠️ reflect claims I no longer stand behind.

# Ralph Loops: What They Are and Why They Matter

## The Technique

Ralph loops (originated by Geoffrey Huntley, who began developing the concept in early 2025) are bash while-loops that feed the same prompt to an AI coding agent (Claude Code, Cursor CLI) until a machine-verifiable completion condition is met. Named after Ralph Wiggum — perpetually confused, never stops trying, occasionally succeeds.

The mechanism:
1. Define a completion condition (tests pass, linter clean, build succeeds)
2. Run the agent in a loop against the codebase
3. When context gets polluted with failed attempts, nuke the conversation and restart fresh
4. The agent reads its previous work from git and the filesystem, not from its own memory
5. Repeat until done. Walk away. Sleep. Run multiple loops in parallel.

## ⚠️ The Insight That Outlasted the Technique

~~The bash loop was obsolete within weeks — coding agents (Claude Code sub-agents, Cursor background agents) absorbed parallel autonomous iteration as a native feature. Nobody writes the bash loop anymore.~~

**Correction:** The bash loop is not obsolete. As of February 2026, native agent orchestration (Claude Code task mode, subagents, the official Ralph plugin) still runs within a single session and suffers from context degradation. The community — including Matt Pocock and Huntley himself — maintains that bash-as-orchestrator with fresh context per iteration produces reliably better results than letting the LLM orchestrate itself. People are very much still writing the bash loop.

What persists is the mental model shift:

- **Filesystem as truth**: State lives in git and files, not in the LLM's context window. Fresh context on each invocation prevents accumulated failures from poisoning reasoning. Selective forgetting enables thinking; perfect memory prevents it.
- **Completion conditions over supervision**: The human's job is defining what "done" looks like in machine-verifiable terms, not babysitting each iteration.
- **Orchestration over collaboration**: The LLM is a programmable computer you point at problems, not a pair programmer you have conversations with.
- **Cycle time is less important than walkaway-ability**: Even slow feedback loops (hour-long builds, hardware flash cycles) become viable when running unattended in parallel 24/7.

## Applicability Beyond Web Development

The original hype centered on web/PWA development where feedback loops are fast. But the decomposition principle applies more broadly:

- **Embedded systems**: Separate hardware-neutral code (virtualizable, fast loops) from hardware-specific code (slower loops with target access). Most BSP work is adjusting vendor baselines, which is diffable and loopable.
- **Cloud/infrastructure**: Everything except `terraform apply` to production is loopable. Services, APIs, pipelines, IaC validation — all have testable completion conditions.
- **Mobile native**: Scriptable validation (simulator launch, UI tests, screenshot comparison) makes it loopable, just slower. The friction of native mobile CI/CD is itself an argument for evaluating PWAs.
- **Non-code domains**: Any task where output is machine-verifiable (image similarity scores, structural validation, format compliance) can follow the same pattern.

## ⚠️ Historical Context

~~Ralph loops existed as a distinct technique for roughly two weeks in January 2025 before being absorbed into the tools themselves. Their significance is as the moment the developer community's mental model shifted from "AI as autocomplete I supervise" to "AI as autonomous iterator I orchestrate." The specific implementation is a historical footnote; the paradigm shift is permanent.~~

**Correction:** Ralph loops were not absorbed into the tools in any meaningful sense. Anthropic shipped an official Ralph plugin and native task management, but these operate within a single context window and do not solve the fundamental problem. Huntley has moved on to "The Weaving Loom" — infrastructure for evolutionary software — but the original bash loop technique remains the foundation that everything else builds on. The implementation is not a historical footnote; it's still the most reliable approach for autonomous agent work as of this writing.
