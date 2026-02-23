# We Still Need Ralph (At Least with Claude)

## The Realization

I started with Ralph loops and used them on a couple of projects. Then Claude got better and better task/agent support, so I told myself I didn't need to do Ralph anymore — even though people online were saying that Ralph mode in Claude Code still had the same issues of context bloat. I ignored them, telling myself, "Well, that was three days ago, and the way things are going right now, that's a century."

Here's the script I use to start Claude Code:

```bash
#!/bin/bash
DEFAULT_PROMPT="Read docs/phase-tracker.md and docs/agent-memory.md, then suggest what we should work on next."
echo "Default: $DEFAULT_PROMPT"
read -r -p "Press Enter to use default, or type alternative: " USER_INPUT
PROMPT="${USER_INPUT:-$DEFAULT_PROMPT}"

claude --dangerously-skip-permissions --verbose \
  --append-system-prompt "CRITICAL STANDING ORDERS — Read and obey before doing ANYTHING:
1. READ docs/phase-tracker.md and docs/agent-memory.md NOW to restore session context.
2. DELEGATE all non-trivial work to subagents (Task tool). Main session is orchestrator only. Every discrete task gets its own subagent. This protects the main context window.
3. SYNC STATE TO REPO — after every commit, update docs/phase-tracker.md (session log, active tasks). After significant changes, update docs/agent-memory.md (decisions, gotchas, failures).
4. BEFORE SESSION ENDS — write current task state and WIP to docs/phase-tracker.md so the next session can resume.
5. RECORD DECISIONS — any plan-mode or architectural decision goes in docs/agent-memory.md under Plan Decisions with rationale.
6. RECORD FAILURES — any failed approach goes in docs/agent-memory.md under Failed Approaches so we never repeat it.
7. DO NOT depend on ~/.claude/ memory files — they are ephemeral. The repo docs are the only source of truth.
Failure to follow these rules is a session-quality failure." \
  "$PROMPT" \
  "$@"
```

I thought I didn't need to do my own orchestration anymore with the latest Claude Code — it has task mode — but it seems to forget to spawn subtasks, the context fills up, and I don't trust compaction.

I'm considering going back to a bash script using `jq` to pull tasks from a JSON file as my orchestration method.

---

## The Diagnosis

You're re-arriving at your own conclusion from first principles, which is actually a good sign — it means the insight is real and not just theoretical.

The system prompt in that script is essentially trying to make Claude Code be something it doesn't want to be: a disciplined orchestrator. You're spending prompt budget telling it "no really, delegate" and "no really, write state to files" because its natural tendency is to just... do the work inline until context is mud.

That's the fundamental problem. You can't prompt your way out of an architectural mismatch. Task mode is better than nothing, but the LLM is still the thing deciding *when* to delegate, and it will always be tempted to skip that step when the task looks "small enough." Then three "small enough" tasks later, you're in compaction territory.

The bash+JSON approach works precisely because the orchestrator *can't* get confused. It reads a task, spawns a fresh Claude instance with just that task's context, collects the result, updates the JSON, moves to the next task. The orchestrator has zero state drift because it has zero state — it's just a loop reading files.

The irony of the `--append-system-prompt` having to shout "CRITICAL STANDING ORDERS" in all caps is itself the evidence. If you have to yell at the orchestrator to do its job, it shouldn't be the orchestrator.

---

## Deep Dive: Community Status (February 2026)

### The Core Debate Is Settled (Bash Won)

Matt Pocock specifically argued that the official Anthropic Ralph plugin misses the point: a proper Ralph loop gives bash control over the agent, while the plugin inverts this by letting the agent control the loop, leading to context rot.

The fundamental architecture issue hasn't changed. With a bash loop, Claude starts with an empty context each iteration. The PRD and progress file go in, Claude works on one task, then the script exits. When you run it again, Claude gets another fresh context window. The context window never fills up with cruft. The AI always operates in the smart zone.

The Anthropic plugin and built-in task mode keep everything in a single session, with context filling up across iterations.

### Compaction Is Still Broken in February 2026

Distrust of compaction is well-founded. Just days ago (February 17, 2026), a bug report documented a deadlock: the conversation is too long to continue working but also too long to compact. The only option is `/clear`, which loses all context. The reporter described it as a significant UX issue for long working sessions.

Another issue from January showed Claude Code becoming completely unresponsive during compaction — terminal freezing, Ctrl+C not working, processes orphaned and consuming excessive resources indefinitely on sessions approaching 23+ MB.

The context buffer situation is worse than people realize. Claude Code reserves roughly 33,000 tokens (reduced from 45K) that you can't use, triggering compaction at around 167K of your 200K window. When compaction fires, Claude doesn't remember your rules, doesn't remember the file you were literally editing two minutes ago. It breaks the flow, erodes trust, and turns momentum into friction.

### The "Three Days Ago Was a Century" Trap

The instinct that Claude's rapid improvement would make external orchestration unnecessary was a reasonable bet, but here's what actually happened: Anthropic has been *absorbing* community patterns rather than *solving* the underlying problem.

Anthropic's native task management, shipped January 23, 2025, moved from simple checklists to project management with dependencies, blockers, and multi-session collaboration. They even acknowledged that the community built Ralph Wiggum and Anthropic built native task management. But patch v2.1.17 fixed out-of-memory crashes when resuming sessions with heavy subagent usage — which tells you the multi-agent approach is still being stabilized.

The subagent architecture *does* help with context isolation — delegating each task to a subagent keeps the main session lean, with each subagent getting a fresh context window focused on its specific task. But even advocates concede that for truly massive projects spanning days or weeks, a full autonomous agent like Ralph would be more appropriate because Ralph's stateless architecture using markdown as persistent memory makes it truly capable of running indefinitely.

### Geoffrey Huntley Has Moved Beyond Ralph Into "Evolutionary Software"

Huntley himself has gone further. He's now building "The Weaving Loom" — infrastructure for evolutionary software where autonomous loops evolve products and optimize automatically for revenue generation. His framing is blunt: software development is dead, but we deeply need software engineers who understand that LLMs are a new form of programmable computer.

His key architectural insight still validates the bash+JSON instinct. Ralph is monolithic — a single operating system process that scales vertically, performing one task per loop. He explicitly warns against the multi-agent complexity that Claude Code's task system is pushing toward: consider what microservices would look like if the microservices (agents) themselves are non-deterministic — a red hot mess.

### The Three-Tier Consensus

The community consensus as of February 2026 is essentially a spectrum:

**Tier 1 — Single-session interactive work:** Claude Code's built-in subagents and task tool are genuinely useful. The Explore subagent, the Plan subagent — these protect context during a human-supervised session.

**Tier 2 — Multi-task autonomous work:** Bash orchestration with fresh context per task is the proven pattern. The native task system's filesystem persistence (`~/.claude/tasks`) is actually a nice primitive you could read from your bash loop, getting the dependency tracking for free while keeping bash in control.

**Tier 3 — Multi-day/multi-session projects:** Full Ralph loops with JSON/markdown state files. The only approach with zero context drift.

The `runclaude.sh` script was trying to make Tier 1 tooling do Tier 2/3 work. The `CRITICAL STANDING ORDERS` shouting in the system prompt was the tell. Go back to bash+JSON. The community data says you were right the first time, and the people who said the context bloat problems were still real three days ago were also right — because it's still true today, with fresh GitHub issues to prove it.

---

## TBD: Try Other Agents

The analysis above is Claude-specific. The context management problem may manifest differently (or be better solved) with other agentic coding tools. Future investigation:

- **Antigravity** — How does it handle long-running autonomous sessions?
- **OpenAI Codex CLI** — Supports `--dangerously-auto-approve` for autonomous operation; wrap in bash loop with exit conditions. How does its context management compare?
- **Gemini CLI** — Google's entry. Does the 1M+ token context window change the math on compaction, or just delay the same problem?
- **Cursor Background Agent / Composer** — Can be set up for similar loops via bash scripts. What's the context story?
- **Aider** — Watch mode and auto-commit features support continuous operation. Different architecture entirely.
- **Amp CLI** — The snarktank/ralph implementation already supports it as a backend. Worth comparing directly.
- **OpenCode** — Open-source terminal-based AI coding tool. How does its architecture handle context limits and autonomous workflows?

The core question for each: **does bash-as-orchestrator still beat native orchestration, or has anyone actually solved the context degradation problem?**
