# Marge Project Ã¢â‚¬" Continuation Prompt

Upload the three attached documents, then paste everything below this line into a new chat.

---

## Context

I'm designing **Marge**, a clean-room reimplementation of Home Assistant's functional requirements. The core insight: Home Assistant represents 10 years of community-driven requirements discovery (2000+ integrations, 30+ entity domains, battle-tested automation engine), but its Python runtime is unsuitable for embedded/latency-sensitive home automation hardware. We're using HA as a living spec, not forking the code.

**The name:** Home Assistant Ã¢â€ ' Homer Ã¢â€ ' Marge. She's the one who actually keeps the household running while everyone else causes chaos. Also a nod to the Simpsons lineage in LLM agentic coding Ã¢â‚¬" "Ralph loop" (the viral LLM coding pattern: write code Ã¢â€ ' run tests Ã¢â€ ' feed errors back Ã¢â€ ' iterate) is named after Ralph Wiggum.

**The dual experiment:** This project is exploring two things simultaneously: (1) can you build a production-grade HA workalike, and (2) can LLM-driven agentic coding do the heavy lifting when the specification is rigorous enough? The CTS gives an objective pass/fail signal that doesn't care whether a human or an AI wrote the Rust. The maxim: anything that can be tested can be automated Ã¢â‚¬" including the writing of the code that passes the tests.

I'm a Director of Engineering at a home security / IoT company. 25+ years of experience, embedded systems background. This is a personal project but informed by professional experience shipping hardware products.

## Attached Documents

You should have three files:

1. **marge-sss.md** (MRG-SSS-001) Ã¢â‚¬" System/Subsystem Specification. MIL-STD-498 style. Covers architecture, entity model, automation engine, integration framework, APIs, non-functional requirements, dev roadmap, risk register. Includes a preface explaining the "HA as spec" motivation and the LLM agentic angle.

2. **marge-conformance-tests.md** (MRG-CTS-001) Ã¢â‚¬" Conformance Test Suite Specification. ~1,200 black-box tests in Python/pytest that validate correct behavior through public APIs only (REST, WebSocket, MQTT). Run against HA-legacy: all green. Run against Marge: all green. The test suite IS the executable specification. The SSS explains why; the CTS proves whether.

3. **marge-theory-of-ops.md** (MRG-OPS-001) Ã¢â‚¬" Theory of Operations. How the system lives in the real world: deployment (single static binary, Docker, future OS image), normal operations (process architecture, resource consumption, logging, health monitoring), failure modes and recovery (7 failure classes with timelines), maintenance (atomic binary swap updates, backups, config reload), HA migration path (parallel-run strategy), security, CLI reference, operational checklists.

## Key Architecture Decisions Already Made

- **Rust core** (tokio async): State machine, event bus, automation engine, MQTT broker, HTTP/WS server. Zero GC, <15MB footprint, sub-100Ã‚Âµs state transitions.
- **Go SDK**: Convenience layer for integration developers writing cloud API pollers and REST wrappers.
- **gRPC protocol**: Polyglot integration support Ã¢â‚¬" any language can implement IntegrationService.
- **HA Python shim**: Compatibility layer wrapping existing HA integrations in subprocess with gRPC bridge, giving access to 2000+ integrations on day one.
- **MQTT-native backbone**: All state changes, service calls, events flow through MQTT topics. Not a bolt-on.
- **Integration isolation**: Separate processes via gRPC/MQTT. Crashes can't take down core. Automatic restart with exponential backoff.
- **HA YAML compatibility**: Ã¢â€°Â¥90% configuration.yaml, Ã¢â€°Â¥95% automations.yaml. Pinned to HA 2024.12 baseline.
- **Embedded MQTT broker** (rumqttd) with option for external Mosquitto.
- **SQLite** (rusqlite, WAL mode) for persistence, optional TimescaleDB for long-term storage.
- **TypeScript/React** frontend with WebSocket state sync.

## Key Decisions During Our Discussion

- **Rust over Go for core**: I pushed back on Go for embedded based on professional experience seeing Go fail on constrained devices. GC pauses, minimum memory footprint, binary size all matter. "Go in the cloud is a no-brainer. Go on an embedded device is something I've seen fail."
- **Test suite as the real spec**: The CTS is arguably more important than the SSS. A spec that can't lie (executable tests) is worth more than one that can (narrative document). Pattern from SQLite, LLVM, MariaDB, Web Platform Tests.
- **Characterization test workflow**: Hypothesize Ã¢â€ ' write test Ã¢â€ ' run against HA Ã¢â€ ' observe actual behavior Ã¢â€ ' encode assertion Ã¢â€ ' now Marge must match. Discovers undocumented edge cases rather than guessing at them.
- **LLM agentic implementation**: The project is being developed with heavy LLM agent assistance. The rigorous spec + executable test suite makes this viable Ã¢â‚¬" the feedback loop is: agent writes code, CTS runs, failures feed back, agent iterates. This is Ralph loop with a real spec.

## Open Threads / Next Steps

- **Day in the Life comparison**: The TheoryOps Ã‚Â§1.1 "Day in the Life" currently shows Marge numbers only. We discussed that the functional narrative is identical for both HA-legacy and Marge (same automations, same triggers, same outcomes Ã¢â‚¬" that's the CTS guarantee), but the operational profile differs dramatically (startup time, memory, failure isolation, recovery time). A side-by-side comparison table was considered but not yet added.
- **No code written yet.** All three documents are specifications. The next logical step would be Phase 0 implementation (MQTT broker, state machine, event bus, service registry) or further specification work.
- **The documents cross-reference each other** via document numbers (MRG-SSS-001, MRG-CTS-001, MRG-OPS-001) and the SSS references table includes both companion docs.

## Preferences

- Always use markdown (.md) for documents, never docx.
- I like the MIL-STD-498 document style with irreverent prefaces. Keep the "Department of Not Running Python In Production" energy.
- I prefer depth over breadth. Don't summarize when you can specify.
- I'll push back when something is wrong. Take that as collaboration, not criticism.
