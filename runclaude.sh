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
