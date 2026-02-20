# Service Replacement Methodology -- Socket-Level Shadow Validation

**Document Number:** MRG-SRM-001
**Version:** 0.1.0-DRAFT
**Classification:** UNCLASSIFIED // FOUO
**Date:** 2026-02-20
**Parent Documents:** MRG-ORIGIN-001 (Origin Story), MRG-CTS-001 (Conformance Test Suite)
**Prepared For:** The Department of Not Running Python In Production

---

## 1. ABSTRACT

This document describes a methodology for replacing legacy services in a distributed system without writing a traditional specification or reading the original source code. The approach interposes a man-in-the-middle proxy at the socket layer between communicating services, captures all inter-service traffic to build a behavioral corpus, derives executable assertions from that corpus, builds a replacement, and then runs the original and replacement in parallel -- comparing every response until they are indistinguishable. The system's actual behavior becomes the specification. This methodology generalizes the approach used in the Marge project (MRG-ORIGIN-001), which used Home Assistant's public APIs as a behavioral oracle and a hand-written conformance test suite to validate a clean-room reimplementation. Where Marge relied on manual observation and spec-writing, this methodology automates both through protocol-level capture and shadow validation.

---

## 2. PROBLEM STATEMENT

### 2.1 Why Legacy Services Resist Replacement

Production services accumulate behavior the way coral reefs accumulate calcium: slowly, invisibly, and in patterns that only make sense in context. After five or ten years of operation, a service's behavior is the sum of its original design, every bug fix that became a feature, every undocumented workaround that clients now depend on, every error mode that upstream callers have learned to handle, and every implicit contract that exists only in the timing and ordering of its responses.

This behavior is not written down. It is not in the README. It is not in the API docs, which describe what the service was supposed to do three years ago. It is not in the tests, which cover the happy path and two error cases. The behavior lives in the running process and nowhere else.

### 2.2 Why Traditional Approaches Fail

**Code translation** (rewrite from language A to language B) fails because it confuses implementation with behavior. Two implementations can produce identical output from identical input while having completely different internal structures. Translating the structure does not guarantee translating the behavior -- and usually guarantees translating the bugs.

**Manual specification** fails at scale. A human can document the top 50 API endpoints. They cannot document the interaction between endpoint 37's error response and the retry logic in three upstream services that has been stable for four years and will break the moment it changes.

**Test-suite-first** (the Marge approach) works but is labor-intensive. Marge's CTS was hand-written from API documentation, observed behavior, and iterative debugging. It took significant effort to identify which behaviors mattered. For a system with hundreds of inter-service boundaries, this does not scale.

### 2.3 The Core Insight

The system's actual behavior IS the specification. You do not need to write it -- you need to observe it. Every byte that crosses a socket between two services is a fact about what the system does. Capture enough facts and you have a complete behavioral description. Replay those facts against a replacement and compare the results, and you have a validation oracle.

The socket is the seam. If services communicate over network sockets using a known protocol, every interaction is observable, recordable, and replayable. You do not need source code access. You do not need documentation. You need a proxy and a packet decoder.

---

## 3. METHODOLOGY OVERVIEW

The methodology proceeds in five phases. Each phase has a single objective, a clear input, and a clear output. Phases are sequential; each builds on the artifacts produced by the previous phase.

### Phase 1: INTERCEPT

**Objective:** Deploy a transparent proxy layer that captures all inter-service communication without altering system behavior.

**Input:** A running multi-service system with identified socket-level communication paths.

**Output:** A raw traffic corpus -- timestamped, ordered, complete.

The MITM proxy is deployed between the target service and its callers. It operates in passive RECORD mode: every request and response is captured verbatim, with timestamps, source/destination identifiers, and connection metadata. The proxy must be transparent -- neither the caller nor the target should be aware of its presence. Behavior of the system must remain identical with and without the proxy in the path.

The capture period must be long enough to observe the full behavioral surface of the service. This includes normal operations, error cases, edge cases triggered by time-of-day or calendar events, failure recovery sequences, and any periodic batch operations. For most services, one full operational cycle (24 hours for daily patterns, one month for monthly patterns) provides sufficient coverage.

### Phase 2: DECODE

**Objective:** Transform raw traffic into structured protocol artifacts -- message schemas, request/response pairings, state machines, error catalogs.

**Input:** Raw traffic corpus from Phase 1.

**Output:** A protocol catalog: a structured description of every message type, field, value range, and request/response correlation observed in the corpus.

This phase applies the RPC hint. If the service communicates via protobuf, the raw bytes are decoded using proto descriptors (extracted from the service binary, reflection endpoint, or inferred from wire format). If JSON-RPC, messages are parsed and grouped by method name. If HTTP REST, requests are grouped by path template and method. If MQTT, messages are grouped by topic pattern and payload structure.

The decoder must handle:

- **Schema extraction:** Identify all distinct message types, their fields, and observed value ranges.
- **Request/response pairing:** Correlate outbound requests with their responses (by connection, sequence number, correlation ID, or temporal proximity).
- **State transitions:** Identify sequences where the response to request N depends on the content of requests 1 through N-1 (stateful behavior).
- **Error taxonomy:** Catalog all observed error responses, their triggering conditions, and their frequency.
- **Idempotency analysis:** Identify which operations produce identical responses when repeated versus those that produce different responses (e.g., incrementing counters, generating IDs).

### Phase 3: SPECIFY

**Objective:** Convert the protocol catalog into executable behavioral assertions that can be validated against the live system.

**Input:** Protocol catalog from Phase 2.

**Output:** An executable assertion suite (test suite) that passes when run against the original service.

Each assertion encodes a single observed behavior: "Given this request (with these headers, this body, this preceding state), the service responds with a response matching this shape (these fields, these value constraints, this status code)." Assertions are parameterized from the captured corpus -- the same assertion template may be instantiated hundreds of times with different captured inputs and expected outputs.

The assertion suite is validated by replaying captured traffic against the live original service. Every assertion must pass. If an assertion fails against the original, it encodes a flawed assumption and must be corrected or discarded. This step ensures the assertions describe what the system actually does, not what the observer thinks it should do.

Assertions must account for non-deterministic fields: timestamps, request IDs, UUIDs, sequence numbers, and any other values that change between invocations. These fields are masked or matched by pattern rather than by exact value.

### Phase 4: IMPLEMENT

**Objective:** Build a replacement service that passes the assertion suite.

**Input:** Protocol catalog (Phase 2) and executable assertion suite (Phase 3).

**Output:** A replacement service that produces correct responses for all captured scenarios.

The replacement is built from the protocol catalog (which describes the interface contract) and tested against the assertion suite (which validates behavioral conformance). Implementation language, architecture, and internal design are unconstrained -- the only requirement is that the replacement's observable behavior matches the original's.

This phase is iterative. The assertion suite serves as a regression oracle: implement, run the suite, fix divergences, repeat. The suite also serves as a progress metric -- percentage of passing assertions tracks how close the replacement is to behavioral equivalence.

### Phase 5: SHADOW

**Objective:** Run the original and replacement in parallel on live traffic. Compare every response. Iterate until divergence reaches zero.

**Input:** A replacement service that passes the assertion suite (Phase 4) and the live production system.

**Output:** A validated replacement service, proven equivalent to the original on real traffic over a sustained observation window.

This is the phase that distinguishes the methodology from conventional testing. Captured traffic (Phase 1) and synthetic assertions (Phase 3) can only validate behaviors that were observed during the capture window. Shadow validation tests the replacement against the full, unbounded space of production traffic -- including inputs that were never seen during capture.

The MITM proxy switches to SHADOW mode: every inbound request is forked to both the original and the replacement. The original's response is returned to the caller (zero risk to production). The replacement's response is captured, compared to the original's, and any divergences are logged. The replacement never touches production traffic.

---

## 4. THE MITM PROXY ARCHITECTURE

### 4.1 Position in the Network

The proxy sits between the caller and the target service. It binds to the same address and port that the target previously occupied; the target is relocated to a new address. From the caller's perspective, nothing has changed. From the target's perspective, all requests arrive from the proxy rather than from the original callers. Both are unaware of the interposition.

For containerized environments, this is achieved by manipulating service discovery, DNS, or container networking. For bare-metal deployments, iptables/nftables rules or an explicit reverse proxy configuration accomplish the same result.

### 4.2 Protocol Awareness

The proxy must understand the framing of the protocol in use. It cannot operate on raw TCP streams because it needs to identify message boundaries to correlate requests with responses and to fork messages to multiple backends in SHADOW mode.

Supported framing strategies include:

- **HTTP/1.1:** Content-Length or chunked transfer-encoding delimit message bodies.
- **HTTP/2:** Frame-level parsing (HEADERS, DATA, RST_STREAM). Multiplexed streams require per-stream tracking.
- **gRPC:** HTTP/2 framing with protobuf length-prefixed messages inside DATA frames.
- **Protobuf (raw):** Varint length-prefix followed by serialized message bytes.
- **MQTT:** Fixed header with remaining-length encoding. Packet type identified by first nibble.
- **JSON-RPC:** Newline-delimited or HTTP-wrapped. Correlation via `id` field.
- **Custom binary:** Pluggable decoder with user-supplied framing description (header length, length-field offset, endianness).

### 4.3 Operating Modes

The proxy supports three modes, selectable at runtime:

**RECORD (passive capture).** All traffic passes through unmodified. Every request and response is written to the capture store with timestamps, connection identifiers, and protocol-decoded metadata. No modification, no duplication, no added latency beyond the unavoidable copy.

**REPLAY (offline testing).** The proxy replays captured requests from the corpus against a target service (original or replacement) and compares the responses against the captured originals. This is used during Phase 3 (assertion validation) and Phase 4 (replacement testing) without requiring live callers.

**SHADOW (parallel comparison).** Every inbound request is forwarded to both the original service and the replacement service. The original's response is returned to the caller. Both responses are passed to the comparison engine. Divergences are logged. The replacement's response is discarded (never returned to the caller).

In SHADOW mode, the proxy must handle the case where the original and replacement respond at different speeds. The caller receives the original's response as soon as it is available, with no added latency. The replacement's response is awaited asynchronously; if it times out, a timeout divergence is logged.

### 4.4 Pluggable Codec Layer

The proxy uses a codec abstraction to decode raw bytes into structured messages. Codecs are loaded based on the RPC hint provided at deployment time. Each codec implements:

- `decode(bytes) -> Message`: Parse raw bytes into a structured representation.
- `encode(Message) -> bytes`: Serialize a structured message back to wire format.
- `correlate(request, response) -> bool`: Determine whether a response corresponds to a given request (by ID, sequence number, or connection context).
- `normalize(Message) -> Message`: Strip non-deterministic fields (timestamps, IDs) for comparison purposes.

Codecs exist for protobuf, JSON, MessagePack, CBOR, MQTT payloads, and raw binary. Custom codecs can be provided as shared libraries or WASM modules.

### 4.5 Comparison Engine

The comparison engine performs deep structural comparison of two responses (original and replacement) and classifies any differences. It operates on the normalized, decoded message representation -- not on raw bytes.

Comparison rules are configurable per field:

- **Exact match:** Field values must be identical (default).
- **Pattern match:** Field values must match a regex or structural pattern (for IDs, timestamps).
- **Ignore:** Field is excluded from comparison entirely (for fields known to be non-deterministic).
- **Set equality:** For collections where ordering is not semantically significant, compare as unordered sets rather than ordered lists.
- **Numeric tolerance:** For floating-point fields, compare within an epsilon.

### 4.6 Divergence Log

Every divergence detected by the comparison engine is written to a structured log with the following fields:

| Field | Description |
|---|---|
| `timestamp` | When the divergence was detected |
| `request_id` | Identifier of the triggering request |
| `request_summary` | Decoded request (method, path, key parameters) |
| `original_response` | The original service's response (decoded) |
| `replacement_response` | The replacement service's response (decoded) |
| `diff` | Structured diff showing exactly which fields diverged |
| `classification` | Semantic, cosmetic, or temporal (see Section 5.3) |
| `severity` | Critical, warning, or info |

The divergence log is the primary debugging artifact during Phase 5. It tells the developer exactly where the replacement's behavior differs from the original's and provides the input needed to reproduce the divergence in isolation.

---

## 5. SHADOW VALIDATION PROTOCOL

### 5.1 Traffic Forking

In SHADOW mode, the proxy maintains two downstream connections: one to the original service and one to the replacement. For every inbound request:

1. The request is forwarded verbatim to the original service.
2. A copy of the request is forwarded verbatim to the replacement service.
3. The original's response is returned to the caller immediately.
4. Both responses are passed to the comparison engine.
5. If the comparison detects a divergence, it is written to the divergence log.

The caller's experience is identical to communicating directly with the original service. Latency overhead is limited to the proxy's forwarding cost (typically sub-millisecond). The replacement's processing time does not affect the caller.

### 5.2 Stateful Considerations

For stateful services, the original and replacement must process the same sequence of requests in the same order. The proxy ensures this by forwarding requests synchronously to both backends for the same logical session. If the service uses connection-level state (e.g., an authenticated session), the proxy maintains separate sessions to each backend, initialized with the same credentials and setup sequence.

State synchronization between the original and replacement is the hardest problem in shadow validation. Three strategies exist, in order of increasing complexity:

- **Stateless services:** No synchronization needed. Each request is independent. This is the easy case.
- **Read-heavy services:** The replacement reads from the same backing store as the original. Write operations are performed only by the original; the replacement observes the resulting state via the shared store. Divergences in write operations are logged but do not corrupt shared state.
- **Fully stateful services:** Both services maintain independent state. Initial state is cloned. The proxy ensures both see the same request sequence. Over time, state may drift if the replacement processes requests differently. Periodic state snapshots and comparison detect drift.

### 5.3 Divergence Classification

Not all divergences are equal. The comparison engine classifies each divergence into one of three categories:

**Semantic divergence.** The replacement produced a substantively different answer. A query for user data returned a different user. A calculation returned a different result. An error was returned where a success was expected. These are bugs in the replacement. They must be fixed.

**Cosmetic divergence.** The replacement produced the same answer in a different format. Field ordering differs in a JSON object. A timestamp uses a different timezone representation. A string uses different capitalization. These are not bugs but may indicate assumptions that downstream callers depend on. They should be investigated and either normalized or accepted.

**Temporal divergence.** The replacement produced the correct answer but at a different time. A response that the original returned in 5ms took the replacement 50ms. A polling endpoint returned stale data because the replacement's cache had not yet been populated. These may or may not matter depending on the system's latency requirements. They should be tracked as a separate metric.

### 5.4 Convergence Metric

The convergence metric is the ratio of semantically identical responses to total responses, measured over a rolling window:

```
convergence = (total_requests - semantic_divergences) / total_requests
```

Cosmetic and temporal divergences are tracked separately and do not reduce the convergence metric (though they are reported and should trend toward zero).

The replacement is considered validated when:

1. Convergence has been at 100% for a sustained observation window (minimum: one full operational cycle of the system -- typically 24 hours to 7 days).
2. The observation window included all known periodic behaviors (daily jobs, weekly reports, monthly aggregations).
3. The observation window included at least one instance of each error mode observed during Phase 1.

When these conditions are met, the replacement is a behavioral clone of the original. Cut over.

### 5.5 Cutover

Cutover is the simplest step in the methodology. The proxy stops forwarding to the original and routes all traffic to the replacement. From the caller's perspective, nothing changes -- the proxy address is the same, the protocol is the same, the responses are the same.

The original service is not decommissioned immediately. It is kept running in a dormant state (not receiving traffic) for a rollback window. If a previously unobserved input triggers a divergence in the replacement that was not caught during shadow validation, traffic can be rerouted back to the original within seconds.

---

## 6. RELATIONSHIP TO MARGE

### 6.1 Marge as Prior Art

The Marge project (MRG-ORIGIN-001) replaced Home Assistant's Python core with a Rust implementation. It used HA's REST API, WebSocket API, and MQTT protocol as the behavioral surface -- the observable interface through which correctness was defined and measured.

Marge's approach followed the same philosophical arc as this methodology:

1. **Observe the original's behavior** through its public interfaces.
2. **Encode that behavior as executable assertions** (the CTS -- Conformance Test Suite).
3. **Build a replacement** that passes those assertions.
4. **Validate via parallel execution** (the scenario driver ran identical sequences against both HA and Marge and compared results).

### 6.2 What This Methodology Automates

Marge's CTS was hand-written. A human read HA's API documentation, observed its behavior through manual testing and exploratory interaction, identified which behaviors mattered, and wrote assertions encoding those behaviors. This worked because HA has extensive public documentation and a well-defined API surface.

This methodology automates the observation and assertion-generation phases via protocol-level capture. Instead of a human reading documentation and writing tests, the MITM proxy captures every interaction and the DECODE phase extracts structure from the captures. The result is the same -- an executable behavioral specification -- but the process scales to services with no documentation, no public API spec, and thousands of internal RPC methods.

### 6.3 What This Methodology Adds

Marge validated its replacement primarily through the CTS: a finite set of assertions run as a batch. The CTS covered the known behavioral surface but could not, by construction, cover behaviors that the test author did not anticipate.

Shadow validation (Phase 5) addresses this gap. By running the replacement against live, unbounded production traffic and comparing every response, it catches behaviors that no finite test suite could anticipate. It is the difference between "we tested 2,000 scenarios and they all passed" and "we tested every scenario that occurred in production for two weeks and they all passed."

### 6.4 The Shared Philosophy

Both approaches rest on the same principle: **the running system is the specification.** Documentation lies. Comments rot. Type signatures describe structure, not behavior. But the system's actual responses to actual inputs are ground truth. If you can observe them, you can encode them. If you can encode them, you can validate a replacement against them.

Tests cannot lie -- they either pass or they do not. A shadow comparison cannot lie -- the responses either match or they do not. This is the only foundation on which safe replacement can be built.

---

## 7. APPLICABILITY AND CONSTRAINTS

### 7.1 When This Methodology Applies

The methodology applies when the following conditions hold:

- **Socket-based communication.** Services communicate over network sockets (TCP, UDP, Unix domain sockets). The communication path has a point where a proxy can be interposed. If services communicate via shared memory, filesystem semaphores, or in-process function calls, there is no socket to intercept.

- **Observable protocol.** The protocol is not end-to-end encrypted between services with keys unavailable to the operator. TLS between services is acceptable if the operator controls the certificate authority and can terminate TLS at the proxy (which is standard in service mesh deployments). Mutual TLS requires the proxy to hold valid client and server certificates.

- **Known or discoverable framing.** The RPC hint is available: the operator knows (or can determine) that the protocol is protobuf, gRPC, JSON-RPC, HTTP REST, MQTT, or another recognized format. Without a framing hint, the proxy cannot identify message boundaries or correlate requests with responses. Protocol fingerprinting (see Section 8) can assist when the hint is unavailable.

- **Deterministic or controllable state.** For stateful services, it must be possible to initialize the replacement with the same state as the original, or to synchronize state between them during shadow validation. If the service's behavior depends on state that cannot be observed or replicated (e.g., in-memory caches populated by an unobservable process), shadow validation will produce false divergences that cannot be resolved.

### 7.2 When This Methodology Is Difficult

The following conditions do not prohibit use of the methodology but significantly increase its complexity:

- **Complex session state.** Services that maintain long-lived sessions with accumulated state (e.g., database connections with transaction isolation, WebSocket connections with subscription state) require the proxy to replicate session setup sequences for both backends. Each session adds synchronization overhead and potential for state drift.

- **Wall-clock time dependence.** Services whose responses depend on the current time (TTLs, token expiration, time-windowed rate limits) will produce temporal divergences that must be filtered from the comparison. If the time dependence is integral to the service's correctness (e.g., a scheduling service), the original and replacement must be synchronized to the same clock source.

- **External randomness.** Services that incorporate random values into responses (UUIDs, nonces, cryptographic challenges) require those fields to be excluded from comparison. If the random values affect subsequent behavior (e.g., a session token generated by the service and used in later requests), the proxy must be aware of the correlation.

- **Fire-and-forget messaging.** Protocols without request/response pairing (e.g., UDP telemetry, MQTT QoS 0 publishes) cannot be validated by response comparison. Validation must instead compare the side effects of the messages (state changes in downstream systems, database writes, metric emissions).

- **Streaming protocols.** Long-lived streaming connections (WebSocket, gRPC server-streaming, SSE) produce responses over extended periods. The proxy must compare streaming output incrementally rather than as a single response. Ordering, timing, and completeness of the stream all become comparison dimensions.

- **Unobservable internal state.** If the "correct" response depends on state that is not visible through the service's external interface (e.g., an in-memory LRU cache), shadow validation cannot distinguish between a divergence caused by a bug and a divergence caused by different internal state. This is the fundamental limit of black-box validation.

---

## 8. FUTURE WORK

### 8.1 Automated Codec Detection

The current methodology requires an RPC hint -- the operator must know what protocol the services use. Protocol fingerprinting from raw bytes could eliminate this requirement. Heuristics exist for identifying common protocols from their wire format: HTTP by its ASCII verb line, protobuf by its field tag encoding, MQTT by its fixed header structure, JSON by its leading byte. A fingerprinting layer that automatically selects the correct codec would reduce deployment friction and enable use in systems where the protocol is unknown or undocumented.

### 8.2 AI-Assisted Specification Generation

Phase 3 (SPECIFY) currently produces assertions mechanically from observed request/response pairs. A language model could analyze the protocol catalog and generate higher-level behavioral specifications: "This endpoint implements pagination with cursor-based navigation," "This RPC method is idempotent," "This error code is returned when the referenced entity does not exist." These specifications would be more readable, more maintainable, and more useful as documentation than raw assertion lists.

### 8.3 Continuous Shadow Validation

Phase 5 is currently a pre-cutover validation step. In a continuous deployment pipeline, shadow validation could run permanently: every new version of a service is deployed as a shadow alongside the current version, with divergences reported as CI/CD signals. This is a variant of canary deployment where the canary never receives real traffic but is validated against it in real time.

### 8.4 Multi-Service Orchestration

The methodology as described replaces one service at a time. In a system with many interdependent services, replacements must be sequenced in dependency order: leaf services first (those with no downstream dependencies), then their callers, progressing toward the system's entry points. A multi-service orchestrator would manage this sequencing, track cross-service state dependencies, and coordinate the shadow validation of services whose inputs come from other services that are themselves being replaced.

### 8.5 Differential Fuzzing

The shadow validation corpus is bounded by production traffic. Differential fuzzing extends validation to inputs that production has never seen. A fuzzer generates syntactically valid but semantically novel requests (mutated from the captured corpus), sends them to both the original and replacement, and compares responses. This discovers divergences in error handling, boundary conditions, and edge cases that production traffic may never exercise.

---

## 9. REFERENCES

| Document | Title |
|---|---|
| MRG-ORIGIN-001 | The Origin of Marge |
| MRG-SSS-001 | MARGE System/Subsystem Specification |
| MRG-CTS-001 | MARGE Conformance Test Suite Specification |
| MRG-OPS-001 | MARGE Theory of Operations |
