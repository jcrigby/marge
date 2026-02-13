//! State persistence via SQLite + WAL (Phase 2 §1.1)
//!
//! Write-through on every state change with async batch coalescing (100ms).
//! On startup, restores all entity states before accepting connections.
//! Auto-purges history older than configurable retention (default 10 days).

use std::path::Path;
use std::time::Duration;

use rusqlite::{params, Connection};
use tokio::sync::mpsc;

use crate::state::{StateChangedEvent, StateMachine};

/// A state change queued for persistence.
struct PendingWrite {
    entity_id: String,
    state: String,
    attributes_json: String,
    last_changed: String,
    last_updated: String,
}

/// Open (or create) the SQLite database with WAL mode.
fn open_db(path: &Path) -> rusqlite::Result<Connection> {
    let conn = Connection::open(path)?;
    conn.pragma_update(None, "journal_mode", "wal")?;
    conn.pragma_update(None, "synchronous", "NORMAL")?;
    conn.pragma_update(None, "busy_timeout", 5000)?;

    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS entity_states (
            entity_id   TEXT PRIMARY KEY,
            state       TEXT NOT NULL,
            attributes  TEXT NOT NULL DEFAULT '{}',
            last_changed TEXT NOT NULL,
            last_updated TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS state_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id   TEXT NOT NULL,
            state       TEXT NOT NULL,
            attributes  TEXT NOT NULL DEFAULT '{}',
            last_changed TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            recorded_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );

        CREATE INDEX IF NOT EXISTS idx_history_entity
            ON state_history(entity_id, recorded_at);
        CREATE INDEX IF NOT EXISTS idx_history_recorded
            ON state_history(recorded_at);",
    )?;

    Ok(conn)
}

/// Restore all persisted entity states into the state machine.
/// Called once at startup before accepting connections.
pub fn restore(db_path: &Path, state_machine: &StateMachine) -> anyhow::Result<usize> {
    let conn = open_db(db_path)?;
    let mut stmt = conn.prepare(
        "SELECT entity_id, state, attributes, last_changed, last_updated FROM entity_states",
    )?;

    let mut count = 0usize;
    let rows = stmt.query_map([], |row| {
        Ok((
            row.get::<_, String>(0)?,
            row.get::<_, String>(1)?,
            row.get::<_, String>(2)?,
        ))
    })?;

    for row in rows {
        let (entity_id, state, attrs_json) = row?;
        let attrs: serde_json::Map<String, serde_json::Value> =
            serde_json::from_str(&attrs_json).unwrap_or_default();
        state_machine.set(entity_id, state, attrs);
        count += 1;
    }

    Ok(count)
}

/// Spawn the async persistence writer.
///
/// Returns an mpsc sender. The caller feeds StateChangedEvents into it;
/// the writer batches them with 100ms coalescing and writes to SQLite.
pub fn spawn_writer(
    db_path: std::path::PathBuf,
    retention_days: u32,
) -> mpsc::UnboundedSender<StateChangedEvent> {
    let (tx, rx) = mpsc::unbounded_channel::<StateChangedEvent>();

    // The SQLite writer runs on a dedicated blocking thread so it never
    // starves the tokio runtime.
    tokio::task::spawn_blocking(move || {
        writer_loop(db_path, retention_days, rx);
    });

    tx
}

/// The blocking writer loop.  Drains the channel with 100ms coalescing.
fn writer_loop(
    db_path: std::path::PathBuf,
    retention_days: u32,
    mut rx: mpsc::UnboundedReceiver<StateChangedEvent>,
) {
    let conn = match open_db(&db_path) {
        Ok(c) => c,
        Err(e) => {
            tracing::error!("Recorder: failed to open DB: {}", e);
            return;
        }
    };

    // Purge old history on startup
    if let Err(e) = purge_history(&conn, retention_days) {
        tracing::warn!("Recorder: purge error: {}", e);
    }

    let mut batch: Vec<PendingWrite> = Vec::with_capacity(128);
    let coalesce = Duration::from_millis(100);
    let purge_interval = Duration::from_secs(3600); // purge check every hour
    let mut last_purge = std::time::Instant::now();

    loop {
        // Block on first event (or exit if channel closed)
        match rx.blocking_recv() {
            Some(event) => batch.push(to_pending(&event)),
            None => break,
        }

        // Coalesce: drain anything that arrives within 100ms
        let deadline = std::time::Instant::now() + coalesce;
        loop {
            let remaining = deadline.saturating_duration_since(std::time::Instant::now());
            if remaining.is_zero() {
                break;
            }
            // Try recv with a timeout using a spin-sleep approach
            // (mpsc::UnboundedReceiver has no timeout; we use try_recv with short sleeps)
            match rx.try_recv() {
                Ok(event) => batch.push(to_pending(&event)),
                Err(mpsc::error::TryRecvError::Empty) => {
                    std::thread::sleep(Duration::from_millis(10).min(remaining));
                }
                Err(mpsc::error::TryRecvError::Disconnected) => {
                    // Flush remaining and exit
                    if !batch.is_empty() {
                        flush_batch(&conn, &batch);
                    }
                    return;
                }
            }
        }

        // Flush the batch
        if !batch.is_empty() {
            flush_batch(&conn, &batch);
            batch.clear();
        }

        // Periodic purge
        if last_purge.elapsed() >= purge_interval {
            if let Err(e) = purge_history(&conn, retention_days) {
                tracing::warn!("Recorder: purge error: {}", e);
            }
            last_purge = std::time::Instant::now();
        }
    }
}

fn to_pending(event: &StateChangedEvent) -> PendingWrite {
    PendingWrite {
        entity_id: event.new_state.entity_id.clone(),
        state: event.new_state.state.clone(),
        attributes_json: serde_json::to_string(&event.new_state.attributes)
            .unwrap_or_else(|_| "{}".to_string()),
        last_changed: event.new_state.last_changed.to_rfc3339(),
        last_updated: event.new_state.last_updated.to_rfc3339(),
    }
}

fn flush_batch(conn: &Connection, batch: &[PendingWrite]) {
    // Use a transaction for the whole batch
    let tx = match conn.unchecked_transaction() {
        Ok(t) => t,
        Err(e) => {
            tracing::error!("Recorder: begin tx failed: {}", e);
            return;
        }
    };

    for w in batch {
        // Upsert current state
        if let Err(e) = tx.execute(
            "INSERT INTO entity_states (entity_id, state, attributes, last_changed, last_updated)
             VALUES (?1, ?2, ?3, ?4, ?5)
             ON CONFLICT(entity_id) DO UPDATE SET
                state = excluded.state,
                attributes = excluded.attributes,
                last_changed = excluded.last_changed,
                last_updated = excluded.last_updated",
            params![w.entity_id, w.state, w.attributes_json, w.last_changed, w.last_updated],
        ) {
            tracing::error!("Recorder: upsert error: {}", e);
        }

        // Append to history
        if let Err(e) = tx.execute(
            "INSERT INTO state_history (entity_id, state, attributes, last_changed, last_updated)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![w.entity_id, w.state, w.attributes_json, w.last_changed, w.last_updated],
        ) {
            tracing::error!("Recorder: history insert error: {}", e);
        }
    }

    if let Err(e) = tx.commit() {
        tracing::error!("Recorder: commit failed: {}", e);
    }
}

/// Query state history for an entity within a time range.
/// Returns Vec of (state, attributes_json, recorded_at).
pub fn query_history(
    db_path: &Path,
    entity_id: &str,
    start: &str,
    end: &str,
) -> anyhow::Result<Vec<HistoryEntry>> {
    let conn = open_db(db_path)?;
    let mut stmt = conn.prepare(
        "SELECT state, attributes, last_changed, last_updated, recorded_at
         FROM state_history
         WHERE entity_id = ?1 AND recorded_at >= ?2 AND recorded_at <= ?3
         ORDER BY recorded_at ASC
         LIMIT 10000",
    )?;

    let rows = stmt.query_map(params![entity_id, start, end], |row| {
        Ok(HistoryEntry {
            state: row.get(0)?,
            attributes: row.get(1)?,
            last_changed: row.get(2)?,
            last_updated: row.get(3)?,
            recorded_at: row.get(4)?,
        })
    })?;

    let mut entries = Vec::new();
    for row in rows {
        entries.push(row?);
    }
    Ok(entries)
}

/// Query state history for multiple entities.
pub fn query_history_multi(
    db_path: &Path,
    entity_ids: &[String],
    start: &str,
    end: &str,
) -> anyhow::Result<std::collections::HashMap<String, Vec<HistoryEntry>>> {
    let conn = open_db(db_path)?;
    let mut result = std::collections::HashMap::new();

    for entity_id in entity_ids {
        let mut stmt = conn.prepare(
            "SELECT state, attributes, last_changed, last_updated, recorded_at
             FROM state_history
             WHERE entity_id = ?1 AND recorded_at >= ?2 AND recorded_at <= ?3
             ORDER BY recorded_at ASC
             LIMIT 10000",
        )?;

        let rows = stmt.query_map(params![entity_id, start, end], |row| {
            Ok(HistoryEntry {
                state: row.get(0)?,
                attributes: row.get(1)?,
                last_changed: row.get(2)?,
                last_updated: row.get(3)?,
                recorded_at: row.get(4)?,
            })
        })?;

        let mut entries = Vec::new();
        for row in rows {
            entries.push(row?);
        }
        if !entries.is_empty() {
            result.insert(entity_id.clone(), entries);
        }
    }
    Ok(result)
}

#[derive(Debug, serde::Serialize)]
pub struct HistoryEntry {
    pub state: String,
    pub attributes: String,
    pub last_changed: String,
    pub last_updated: String,
    pub recorded_at: String,
}

/// Query aggregated statistics for a numeric entity.
/// Returns hourly buckets with min, max, mean, count.
pub fn query_statistics(
    db_path: &Path,
    entity_id: &str,
    start: &str,
    end: &str,
) -> anyhow::Result<Vec<StatsBucket>> {
    let conn = open_db(db_path)?;
    let mut stmt = conn.prepare(
        "SELECT state, recorded_at
         FROM state_history
         WHERE entity_id = ?1 AND recorded_at >= ?2 AND recorded_at <= ?3
         ORDER BY recorded_at ASC
         LIMIT 100000",
    )?;

    let rows = stmt.query_map(params![entity_id, start, end], |row| {
        Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
    })?;

    // Group by hour and compute aggregates
    let mut buckets: std::collections::BTreeMap<String, Vec<f64>> = std::collections::BTreeMap::new();
    for row in rows {
        let (state_str, recorded_at) = row?;
        if let Ok(val) = state_str.parse::<f64>() {
            // Extract hour bucket: "2026-02-13T14" from "2026-02-13T14:30:00Z"
            let hour = if recorded_at.len() >= 13 {
                &recorded_at[..13]
            } else {
                &recorded_at
            };
            buckets.entry(hour.to_string()).or_default().push(val);
        }
    }

    let result = buckets.into_iter().map(|(hour, values)| {
        let count = values.len();
        let sum: f64 = values.iter().sum();
        let min = values.iter().cloned().fold(f64::INFINITY, f64::min);
        let max = values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        StatsBucket {
            hour,
            min,
            max,
            mean: sum / count as f64,
            count,
        }
    }).collect();

    Ok(result)
}

#[derive(Debug, serde::Serialize)]
pub struct StatsBucket {
    pub hour: String,
    pub min: f64,
    pub max: f64,
    pub mean: f64,
    pub count: usize,
}

fn purge_history(conn: &Connection, retention_days: u32) -> rusqlite::Result<usize> {
    let cutoff = chrono::Utc::now()
        - chrono::Duration::days(retention_days as i64);
    let cutoff_str = cutoff.to_rfc3339();
    let deleted = conn.execute(
        "DELETE FROM state_history WHERE recorded_at < ?1",
        params![cutoff_str],
    )?;
    if deleted > 0 {
        tracing::info!("Recorder: purged {} history rows older than {} days", deleted, retention_days);
    }
    Ok(deleted)
}
