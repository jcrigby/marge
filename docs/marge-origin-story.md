# The Origin of Marge

**Document Number:** MRG-ORIGIN-001  
**Version:** 0.1.0-DRAFT  
**Classification:** UNCLASSIFIED // FOUO  
**Date:** 2026-02-20  
**Prepared For:** The Department of Not Running Python In Production  

---

## 0. THE INCITING INCIDENT

On February 4, 2026, Anthropic published an engineering blog post about using Claude to rewrite a C compiler in Rust. A few days later, Nate B Jones — a YouTuber who covers AI developments — put out a video about it. In the video, he joked that Anthropic should try something actually hard next, not a toy.

That landed. What if you pointed Claude Code at something genuinely complex — not a compiler (which is a well-defined formal grammar with decades of test suites), but a sprawling, community-driven, decade-old system with 2,000+ integrations and no formal spec? What if you said: "Replace all the Python in Home Assistant with Rust"?

The answer, arrived at over the course of a Perplexity conversation, was: that's a fun idea for a demo and a terrible idea for a real project.

But the question wouldn't leave.

## 1. THE CONVERSATION THAT CHANGED THE QUESTION

The naive version — point an LLM at Home Assistant's Python codebase and say "rewrite this in Rust" — fails immediately and obviously. Python's dynamic typing, duck-typed patterns, and runtime metaprogramming don't map to Rust. Hundreds of integrations have weird edge cases accumulated over a decade. And HA's codebase moves constantly — any fork would drift within weeks.

But there was a version of this that wasn't naive.

The insight came in stages:

**Stage 1: "Not translation — architecture."** If you ask an LLM to rewrite Python in Rust, it thinks *translation*. It tries to map Python idioms to Rust idioms, line by line, and drowns. But if you ask it to *design a system that does what Home Assistant does*, with a clean message-based boundary, it thinks architecture. Event bus. State machine. Service registry. Transport-agnostic message schemas. A narrow outer contract with a free inner implementation.

**Stage 2: "HA is a living specification."** Home Assistant isn't just code — it's the accumulated result of a decade of community-driven requirements discovery. Thousands of contributors have filed bugs, added integrations, argued about edge cases, and refined behaviors. That corpus of *discovered requirements* is the real asset. The Python implementation is just one way to satisfy those requirements. And not a great one, if your target is a Raspberry Pi.

**Stage 3: "Black box, not white box."** Don't read HA's source code. Don't try to understand its internals. Treat it as an opaque system with a public interface: REST API, WebSocket API, MQTT, YAML configuration. Write tests against that interface. Run them against real Home Assistant. Make them green. Now you have an *executable specification* — thousands of assertions about what a smarthome platform is supposed to do, validated by the system that discovered the requirements in the first place.

**Stage 4: "Now make a different box pass those same tests."** Write the tests first. Validate them against HA. Then build a Rust implementation that passes them. You're not reverse-engineering internals. You're matching a contract. The tests don't care what language is underneath. They don't care if a human or an AI wrote the code. They care about behavior.

By the end of the conversation, the project had a shape: a greenfield Rust system that uses Home Assistant as its own specification, verified by a shared conformance test suite. It also had a name.

Home Assistant → Homer → Marge.

She's the one who actually keeps the household running.

## 2. FROM CONVERSATION TO SPECIFICATION

The Perplexity chat produced the idea. The next step was to make it rigorous.

Within a couple of hours on the same day, working with Claude in a project workspace, the idea became three formal specification documents totaling over 4,000 lines:

**MRG-SSS-001 — System/Subsystem Specification.** MIL-STD-498 style, because if you're going to specify a system, specify it like you mean it. Architecture, entity model (30+ domains), automation engine, integration framework (Rust core, gRPC for polyglot support, Python shim for day-one HA compatibility), REST and WebSocket APIs, non-functional requirements, development phasing, risk register. The works.

**MRG-CTS-001 — Conformance Test Suite Specification.** This is the real weapon. ~1,200 black-box tests in Python/pytest that talk to the system under test exclusively through its public APIs. The workflow: hypothesize a behavior → write a test → run it against real HA → observe what actually happens → encode the assertion. Repeat 1,200 times. Now you have a specification that can't lie.

**MRG-OPS-001 — Theory of Operations.** How the system lives in the real world. Deployment models (single static binary, Docker, future OS image). Normal operations (process architecture, resource budget, logging, health monitoring). Seven classes of failure with recovery timelines. Maintenance procedures. HA migration path. Operational checklists.

The project started under the name "Sentinel," which lasted about five minutes before being replaced by "Marge" when the Claude project was created. Sentinel sounded like a defense contractor's bid. Marge sounded like the system that actually keeps the house running while everyone else causes chaos.

During the specification work, the project crossed paths with an idea making the rounds in the AI-assisted coding community: the "Ralph loop" — named after Ralph Wiggum from The Simpsons, because it's doing something hilariously simple and it works anyway. The loop: LLM writes code → runs tests → reads failures → fixes code → repeat. No human in the loop. Just a test suite and an agent iterating until green.

The plan was to use a Ralph loop for Marge's implementation. But by the time the specs were done and Claude Code was turned loose, it never came to that. Claude Code had already learned delegation — it decomposed work into subagent tasks, dispatched them in parallel, verified results, and moved on. The explicit bash-script loop was unnecessary because the agent had internalized the pattern natively. The Ralph loop was the plan; autonomous delegation was what actually happened.

Marge became a dual experiment:

1. Can you build a production-grade Home Assistant workalike in Rust, using HA itself as the oracle for your test suite?
2. Can LLM-driven agentic coding do the heavy lifting when the specification is rigorous enough?

The answer to the first depends on the answer to the second, which is what makes it interesting.

## 3. THE BET

The bet has two parts.

**Part one:** The hard part of building a smarthome platform is not the software engineering. It's figuring out what the software needs to do. Home Assistant already figured that out over a decade of community-driven iteration. We just need to build it like we mean it — for the hardware it actually runs on.

**Part two:** Anything that can be tested can be automated. Including the writing of the code that passes the tests.

A spec that can't lie (executable tests) is worth more than one that can (narrative document). The SSS explains *why*. The CTS proves *whether*.

## 4. THE HANDOFF

With specifications locked, the project was handed to Claude Code for autonomous implementation.

The engineer's role during the build was: pressing "keep going" between phases.

That's not an exaggeration. Claude Code executed eight implementation phases, wrote 14,916 lines of Rust, built a conformance test harness, created a live demo dashboard, and iterated against the test suite until all 94 Rust unit tests passed. Total wall-clock time: 9.5 hours — and that includes the time spent waiting for the human to review each phase summary and press Enter to proceed. Total human intervention: reading what it did and confirming the next phase should start.

The results spoke for themselves:

| Metric               | Home Assistant | Marge       | Improvement     |
|-----------------------|----------------|-------------|-----------------|
| Docker Image Size     | 1.78 GB        | 90 MB       | 20× smaller     |
| Memory (RSS)          | 179 MB         | 12 MB       | 15× smaller     |
| Cold Startup          | ~94 seconds    | 0.5 ms      | 188,000× faster |
| Recovery After Outage | 20.4 seconds   | 5.7 seconds | 3.6× faster     |
| Average Latency       | 0.75 ms        | 3.5 µs      | 214× faster     |
| API Conformance       | Baseline       | 94/94       | 100%            |

These aren't marginal gains. The Rust implementation runs on hardware that Home Assistant can barely start on.

## 5. WHAT IT MEANS

The conventional use of AI in engineering is autocomplete, code review, pair programming — using a race car to drive to the mailbox. The Marge project inverted the relationship. The human did what humans are good at: studying the problem domain, designing architecture, writing specifications, and defining acceptance criteria. The AI did what AI is good at: grinding through implementation against an objective pass/fail signal, iterating autonomously, and not getting bored.

The value of the engineer shifted from writing code to writing specs that make code verifiable. Once you do that, the implementation becomes parallelizable and automatable. That's not "AI is going to replace programmers." It's "the programmers who survive are the ones who can specify."

The origin story of Marge is someone watching a YouTube video about an AI rewriting a C compiler, thinking "try something actually hard," and discovering that the hard part was never the code.

It was always the spec.

---

*"Don't just translate Python. Help me design a system with a clean outer contract so we can build something new inside."*

*— The prompt that started it, more or less*
