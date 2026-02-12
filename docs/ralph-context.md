# Ralph Loops: What They Were and Why They Matter

## The Technique

Ralph loops (coined by Geoffrey Huntley, January 2025) were bash while-loops that fed the same prompt to an AI coding agent (Claude Code, Cursor CLI) until a machine-verifiable completion condition was met. Named after Ralph Wiggumâ€”perpetually confused, never stops trying, occasionally succeeds.

The mechanism:
1. Define a completion condition (tests pass, linter clean, build succeeds)
2. Run the agent in a loop against the codebase
3. When context gets polluted with failed attempts, nuke the conversation and restart fresh
4. The agent reads its previous work from git and the filesystem, not from its own memory
5. Repeat until done. Walk away. Sleep. Run multiple loops in parallel.

## The Insight That Outlasted the Technique

The bash loop was obsolete within weeksâ€”coding agents (Claude Code sub-agents, Cursor background agents) absorbed parallel autonomous iteration as a native feature. Nobody writes the bash loop anymore.

What persists is the mental model shift:

- **Filesystem as truth**: State lives in git and files, not in the LLM's context window. Fresh context on each invocation prevents accumulated failures from poisoning reasoning. Selective forgetting enables thinking; perfect memory prevents it.
- **Completion conditions over supervision**: The human's job is defining what "done" looks like in machine-verifiable terms, not babysitting each iteration.
- **Orchestration over collaboration**: The LLM is a programmable computer you point at problems, not a pair programmer you have conversations with.
- **Cycle time is less important than walkaway-ability**: Even slow feedback loops (hour-long builds, hardware flash cycles) become viable when running unattended in parallel 24/7.

## Applicability Beyond Web Development

The original hype centered on web/PWA development where feedback loops are fast. But the decomposition principle applies more broadly:

- **Embedded systems**: Separate hardware-neutral code (virtualizable, fast loops) from hardware-specific code (slower loops with target access). Most BSP work is adjusting vendor baselines, which is diffable and loopable.
- **Cloud/infrastructure**: Everything except `terraform apply` to production is loopable. Services, APIs, pipelines, IaC validationâ€”all have testable completion conditions.
- **Mobile native**: Scriptable validation (simulator launch, UI tests, screenshot comparison) makes it loopable, just slower. The friction of native mobile CI/CD is itself an argument for evaluating PWAs.
- **Non-code domains**: Any task where output is machine-verifiable (image similarity scores, structural validation, format compliance) can follow the same pattern.

## Historical Context

Ralph loops existed as a distinct technique for roughly two weeks in January 2025 before being absorbed into the tools themselves. Their significance is as the moment the developer community's mental model shifted from "AI as autocomplete I supervise" to "AI as autonomous iterator I orchestrate." The specific implementation is a historical footnote; the paradigm shift is permanent.
