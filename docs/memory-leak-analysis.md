# Memory Leak Analysis -- 3-Day Soak Test

| Field           | Value                                    |
|-----------------|------------------------------------------|
| Document ID     | MLA-001                                  |
| Date            | 2026-02-20                               |
| System          | Marge v0.1.0 (Rust HA reimplementation)  |
| Test Duration   | 72 hours (3 days)                        |
| Configuration   | 37 virtual zigbee2mqtt devices @ 5s interval |

## 1. Scope

This document records the observed memory growth during a 72-hour soak test
of the Marge container, identifies confirmed root causes, catalogs secondary
suspects, and prescribes remediation with a verification plan.

## 2. Observed Behavior

| Metric                 | Value          |
|------------------------|----------------|
| Initial RSS            | ~20 MB         |
| Final RSS (72h)        | 256 MB (OOM)   |
| Container memory limit | 256 MB         |
| Device count           | 37 zigbee2mqtt |
| Publish interval       | 5 seconds      |
| Total messages (est.)  | ~1.9M          |
| Post-recreate RSS      | ~20 MB         |

The container reached its 256 MB memory limit after approximately 3 days of
continuous operation. After `docker compose up -d --force-recreate marge`,
memory returned to the ~20 MB baseline, confirming the growth is a runtime
leak rather than a static allocation issue.

Growth rate: approximately 3.3 MB/hour or 80 MB/day, though the rate is
not perfectly linear due to allocator fragmentation and the mix of
fixed-size and variable-size allocations involved.

## 3. Root Cause Analysis

Two unbounded growth sources were confirmed through code inspection.

### 3.1. RC-1: topic_subscriptions Vec Duplicate Append

**File:** `marge-core/src/discovery.rs`, line 461-466

```rust
fn add_topic_subscription(&self, topic: &str, entity_id: &str) {
    self.topic_subscriptions
        .entry(topic.to_string())
        .or_default()
        .push(entity_id.to_string());
}
```

**Data structure:** `topic_subscriptions: Arc<DashMap<String, Vec<String>>>`
(declared at line 166).

**Mechanism:** Every MQTT discovery message for a device calls
`process_discovery()`, which calls `add_topic_subscription()` for each
state topic, availability topic, and component-specific topic (lines
292-317). The function unconditionally pushes the entity_id string into
the Vec without checking for duplicates.

zigbee2mqtt republishes discovery payloads on reconnection, on
`homeassistant/status` birth messages, and periodically. Over 3 days with
37 devices, each device's state topic accumulates tens of thousands of
duplicate entity_id String allocations.

**Estimated impact:** Each duplicate entry is a heap-allocated String
(~24 bytes String struct + ~30 bytes avg entity_id payload on heap).
With 37 devices and ~50k duplicate appends per topic over 3 days:
37 topics x 50k duplicates x ~54 bytes = ~100 MB.

**Aggravating factor:** `process_state_update()` (line 375-428) iterates
the full Vec on every state message, cloning the entire list at line 381.
This means each 5-second publish cycle iterates over and clones a Vec that
grows without bound. The cloned Vecs are short-lived but create allocator
pressure and fragmentation.

### 3.2. RC-2: last_time_triggers DashMap Key Accumulation

**File:** `marge-core/src/automation.rs`, line 350, 661-662

```rust
last_time_triggers: DashMap<String, String>,
```

```rust
self.last_time_triggers
    .insert(key, current_hhmm.to_string());
```

**Mechanism:** The time-trigger deduplication map stores keys of the form
`"automation_id:HH:MM"` to prevent duplicate fires within the same minute
(line 644). Keys are inserted at line 662 but are only cleared on
`reload()` (line 454: `self.last_time_triggers.clear()`). In normal
operation without reloads, the map grows indefinitely.

Each unique `(automation_id, HH:MM)` pair creates one entry. With 6
automations and 1440 minutes per day, the theoretical maximum is 6 x 1440
= 8640 entries/day. Over 3 days, that is ~26k entries. Each DashMap entry
stores two heap Strings plus DashMap bucket overhead (~120 bytes/entry).

**Estimated impact:** 26k entries x ~120 bytes = ~3 MB. However, the
DashMap's internal bucket structure and allocator fragmentation can amplify
this to 10-20 MB, particularly because keys are never reclaimed, causing
the bucket array to resize upward without ever shrinking.

**Note:** The `last_time_triggers` map's value (the `current_hhmm` string)
is compared at line 648-649, but since time progresses forward, old keys
are never read again -- they are dead weight.

## 4. Secondary Suspects

These items were not confirmed as leak contributors but should be monitored
during soak verification.

### 4.1. SS-1: SQLite WAL Segment Accumulation

**File:** `marge-core/src/recorder.rs`, lines 27-28

```rust
conn.pragma_update(None, "journal_mode", "wal")?;
conn.pragma_update(None, "synchronous", "NORMAL")?;
```

The recorder operates in WAL mode with continuous writes. SQLite performs
automatic checkpoints at the default threshold (1000 pages), but under
sustained high write volume (37 devices x 12 writes/min = 444 inserts/min),
the WAL file can grow if checkpoint throughput falls behind insert
throughput.

The hourly `purge_history()` call (line 221-226) deletes old rows but does
not trigger a `VACUUM` or explicit `wal_checkpoint(TRUNCATE)`, so freed
space remains allocated within the WAL and database files.

**Estimated risk:** Low-to-moderate. SQLite's automatic checkpointing
should keep the WAL bounded under this write rate, but worth verifying with
`PRAGMA wal_checkpoint;` output during the soak.

### 4.2. SS-2: Broadcast Channel Backpressure

**File:** `marge-core/src/state.rs`, line 78 / `main.rs`, line 44

```rust
let state_machine = state::StateMachine::new(4096);
```

The broadcast channel holds up to 4096 `StateChangedEvent` clones. Each
event contains two `EntityState` structs (old + new) with heap-allocated
Strings and serde_json Maps. This is a bounded buffer and does not leak,
but when a subscriber lags (logged at `main.rs:232` and `main.rs:250`),
events are dropped. This does not cause memory growth but does cause data
loss in the recorder and automation engine.

**Estimated risk:** No memory impact. Mentioned for completeness as it
could mask automation misfires during high-load periods.

## 5. Remediation

### 5.1. Fix RC-1: Deduplicate topic_subscriptions

**Change:** Replace `Vec<String>` with `HashSet<String>` in the
`topic_subscriptions` DashMap.

**File:** `marge-core/src/discovery.rs`

Declaration (line 166):
```rust
// Before
topic_subscriptions: Arc<DashMap<String, Vec<String>>>,

// After
topic_subscriptions: Arc<DashMap<String, HashSet<String>>>,
```

Insert logic (line 461-466):
```rust
// Before
fn add_topic_subscription(&self, topic: &str, entity_id: &str) {
    self.topic_subscriptions
        .entry(topic.to_string())
        .or_default()
        .push(entity_id.to_string());
}

// After
fn add_topic_subscription(&self, topic: &str, entity_id: &str) {
    self.topic_subscriptions
        .entry(topic.to_string())
        .or_default()
        .insert(entity_id.to_string());
}
```

**Downstream changes required:**
- `process_state_update()` (line 381): The clone of `ids` returns a
  `HashSet<String>` instead of `Vec<String>`. The for-loop at line 384
  iterates identically; no change needed.
- `remove_topic_subscription()` (line 498-506): `ids.retain()` works on
  `HashSet` (stabilized in Rust 1.36). Alternatively, use `ids.remove()`.

### 5.2. Fix RC-2: Scope last_time_triggers to Current Day

**Change:** Include a date prefix in the key and periodically purge stale
entries, or reset the map at midnight.

**Option A -- Date-prefixed keys with daily clear:**

In `run_time_loop()` (`automation.rs`, line 585-668), the loop already
tracks `last_day` (line 588) and detects day changes (line 601). Add a
clear on day rollover:

```rust
if day != last_day {
    last_day = day;
    self.last_time_triggers.clear();  // <-- add this line
    // ... existing sun time recalculation ...
}
```

This bounds the map to at most one day's worth of entries (~8640 for 6
automations), which is negligible memory.

**Option B -- Replace DashMap with a simpler `RwLock<HashMap<String, String>>`:**

Given the low cardinality (thousands of keys, not millions) and the
single-writer nature of `run_time_loop`, a simpler data structure would
reduce per-entry overhead. This is an optimization, not a correctness fix.

### 5.3. Monitor SS-1: Add WAL Checkpoint Logging

Add a periodic `PRAGMA wal_checkpoint(PASSIVE);` call in the recorder's
purge cycle (line 221-226) and log the returned page counts. This provides
visibility into WAL growth without requiring a code fix.

## 6. Verification Plan

### 6.1. Test Configuration

| Parameter       | Value                      |
|-----------------|----------------------------|
| Container limit | 256 MB (unchanged)         |
| Device count    | 37 virtual zigbee2mqtt     |
| Publish interval| 5 seconds                  |
| Duration        | 24 hours minimum           |
| Monitoring      | `docker stats` sampled every 60s |

### 6.2. Pass Criteria

- RSS remains below 40 MB for the full 24-hour period.
- No OOM kills (`docker inspect --format='{{.State.OOMKilled}}'`).
- Broadcast channel lag warnings (`Recorder listener lagged`) occur
  fewer than 10 times total.
- `topic_subscriptions` entry count per topic equals the number of
  unique entities for that topic (verifiable via debug endpoint or
  tracing).

### 6.3. Monitoring Command

```bash
# Sample RSS every 60 seconds for 24 hours
while true; do
    docker stats marge --no-stream --format \
        '{{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' \
        | ts '%Y-%m-%dT%H:%M:%S' >> /tmp/marge-soak.tsv
    sleep 60
done
```

### 6.4. Regression Gate

After the fix is merged, the soak test described above should be run before
any release that modifies `discovery.rs`, `automation.rs`, or `state.rs`.
A future CTS test should be added that runs 10,000 discovery re-publishes
for a single device and asserts the topic_subscriptions Vec length remains
constant.

## 7. References

| Item | Path |
|------|------|
| Discovery engine | `marge-core/src/discovery.rs` |
| Automation engine | `marge-core/src/automation.rs` |
| Recorder / SQLite | `marge-core/src/recorder.rs` |
| State machine | `marge-core/src/state.rs` |
| Main entry point | `marge-core/src/main.rs` |
