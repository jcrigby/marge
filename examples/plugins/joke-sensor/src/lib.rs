//! joke-sensor -- Example Marge WASM plugin
//!
//! Demonstrates the Marge plugin architecture by fetching random jokes from
//! a public API and publishing them as `sensor.joke`.
//!
//! # Plugin Lifecycle
//!
//! 1. Marge loads the `.wasm` file from `/config/plugins/`.
//! 2. The host calls `init()` once. We set `sensor.joke` to "Loading...".
//! 3. The host calls `poll()` every 60 seconds. Each poll fetches a new
//!    joke via `marge_http_get` and updates `sensor.joke`.
//!
//! # Memory Model
//!
//! WASM plugins communicate with the Marge host entirely through linear
//! memory. The plugin must:
//!
//! - **Export** its `memory` so the host can read/write it.
//! - Pass string data by writing it into its own memory first, then handing
//!   the host a `(pointer, length)` pair.
//! - For host functions that return data (like `marge_http_get`), the plugin
//!   allocates a buffer in its own memory and passes `(buf_ptr, buf_len)`.
//!   The host writes into that buffer and returns how many bytes it wrote.
//!
//! # Host Functions (imported from "env" module)
//!
//! ```text
//! marge_log(level: i32, msg_ptr: i32, msg_len: i32)
//!     Log a message. Levels: 0=error, 1=warn, 2=info, 3=debug.
//!
//! marge_set_state(entity_ptr: i32, entity_len: i32, state_ptr: i32, state_len: i32)
//!     Set an entity's state value.
//!
//! marge_get_state(entity_ptr: i32, entity_len: i32) -> i32
//!     Look up an entity's state. Returns JSON length (0 = not yet implemented).
//!
//! marge_http_get(url_ptr: i32, url_len: i32, buf_ptr: i32, buf_len: i32) -> i64
//!     HTTP GET. Returns packed i64: high 32 bits = status code, low 32 = body bytes written.
//!
//! marge_http_post(url_ptr: i32, url_len: i32,
//!                 body_ptr: i32, body_len: i32,
//!                 buf_ptr: i32, buf_len: i32) -> i64
//!     HTTP POST. Same return convention as http_get.
//! ```
//!
//! # Plugin Exports
//!
//! ```text
//! memory       -- the plugin's linear memory (automatically exported by cdylib)
//! init()       -- called once at load time
//! poll()       -- called periodically (default every 60s)
//! ```

// ---------------------------------------------------------------------------
// Host function imports
// ---------------------------------------------------------------------------
// These are provided by the Marge plugin runtime. The "env" module name must
// match what register_host_functions() in plugins.rs uses for linking.

extern "C" {
    /// Log a message to Marge's tracing infrastructure.
    /// level: 0=error, 1=warn, 2=info, 3=debug
    fn marge_log(level: i32, msg_ptr: i32, msg_len: i32);

    /// Set an entity's state. Both entity_id and state are UTF-8 strings
    /// passed via (pointer, length) pairs in the plugin's linear memory.
    fn marge_set_state(
        entity_ptr: i32,
        entity_len: i32,
        state_ptr: i32,
        state_len: i32,
    );

    /// HTTP GET request. The plugin provides a URL and a response buffer.
    /// Returns packed i64: (status_code << 32) | body_bytes_written.
    fn marge_http_get(
        url_ptr: i32,
        url_len: i32,
        buf_ptr: i32,
        buf_len: i32,
    ) -> i64;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Entity ID for the joke sensor.
const ENTITY_ID: &str = "sensor.joke";

/// Joke API endpoint (returns JSON with "setup" and "punchline" fields).
const JOKE_API_URL: &str = "https://official-joke-api.appspot.com/random_joke";

/// Size of the HTTP response buffer. 4 KB is more than enough for a joke.
const HTTP_BUF_SIZE: usize = 4096;

// ---------------------------------------------------------------------------
// Response buffer
//
// WASM linear memory is flat and exists for the lifetime of the module.
// We use a static mutable buffer that the host writes HTTP response bodies
// into. This is safe because WASM execution is single-threaded.
// ---------------------------------------------------------------------------

/// Static buffer for HTTP response bodies.
/// The host's write_guest_bytes() writes into this region.
///
/// We use `addr_of!` / `addr_of_mut!` to obtain raw pointers without
/// creating intermediate references, which avoids the static_mut_refs
/// lint and is sound because WASM execution is single-threaded.
static mut HTTP_BUF: [u8; HTTP_BUF_SIZE] = [0u8; HTTP_BUF_SIZE];

// ---------------------------------------------------------------------------
// Helper: call host to set entity state
// ---------------------------------------------------------------------------

/// Convenience wrapper around the raw marge_set_state import.
/// Takes Rust string slices and passes the correct pointers/lengths.
fn set_state(entity_id: &str, state: &str) {
    unsafe {
        marge_set_state(
            entity_id.as_ptr() as i32,
            entity_id.len() as i32,
            state.as_ptr() as i32,
            state.len() as i32,
        );
    }
}

/// Convenience wrapper around the raw marge_log import.
fn log(level: i32, msg: &str) {
    unsafe {
        marge_log(level, msg.as_ptr() as i32, msg.len() as i32);
    }
}

// ---------------------------------------------------------------------------
// Minimal JSON string extractor
//
// We avoid pulling in serde/serde_json (which would bloat the .wasm from
// ~2 KB to ~200+ KB). Instead we do a simple substring search for known
// keys in the JSON response. The joke API returns:
//   {"type":"...","setup":"...","punchline":"...","id":...}
// ---------------------------------------------------------------------------

/// Extract the value for a given key from a flat JSON object.
/// Handles escaped quotes within string values.
/// Returns None if the key is not found.
fn json_extract_string<'a>(json: &'a str, key: &str) -> Option<&'a str> {
    // Build the search pattern: "key":"
    // We look for "key":" (with the colon and opening quote) to find the
    // start of the value.
    let mut pattern = [0u8; 64];
    let mut pi = 0;

    // Write "key":
    pattern[pi] = b'"';
    pi += 1;
    for &b in key.as_bytes() {
        if pi >= pattern.len() - 4 {
            return None; // key too long for our fixed buffer
        }
        pattern[pi] = b;
        pi += 1;
    }
    // Write ":"
    pattern[pi] = b'"';
    pi += 1;

    let pattern_slice = &pattern[..pi];
    let json_bytes = json.as_bytes();

    // Find the pattern in the JSON
    let pat_pos = find_subsequence(json_bytes, pattern_slice)?;

    // Skip past the pattern, then skip any whitespace and the colon + optional whitespace + opening quote
    let after_key = pat_pos + pi;
    let rest = &json_bytes[after_key..];

    // Expect : possibly with whitespace, then "
    let mut i = 0;
    // skip whitespace
    while i < rest.len() && (rest[i] == b' ' || rest[i] == b'\t' || rest[i] == b'\n' || rest[i] == b'\r') {
        i += 1;
    }
    // expect colon
    if i >= rest.len() || rest[i] != b':' {
        return None;
    }
    i += 1;
    // skip whitespace
    while i < rest.len() && (rest[i] == b' ' || rest[i] == b'\t' || rest[i] == b'\n' || rest[i] == b'\r') {
        i += 1;
    }
    // expect opening quote
    if i >= rest.len() || rest[i] != b'"' {
        return None;
    }
    i += 1;

    let value_start = after_key + i;

    // Find the closing quote (handle escaped quotes)
    let value_bytes = &json_bytes[value_start..];
    let mut end = 0;
    while end < value_bytes.len() {
        if value_bytes[end] == b'\\' {
            end += 2; // skip escaped character
            continue;
        }
        if value_bytes[end] == b'"' {
            break;
        }
        end += 1;
    }

    if end >= value_bytes.len() {
        return None;
    }

    // Safety: we're slicing from the original UTF-8 json string at byte boundaries
    // that correspond to ASCII delimiters, so the result is valid UTF-8.
    Some(&json[value_start..value_start + end])
}

/// Find the first occurrence of `needle` in `haystack`. Returns the byte offset.
fn find_subsequence(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.is_empty() || needle.len() > haystack.len() {
        return None;
    }
    for i in 0..=(haystack.len() - needle.len()) {
        if &haystack[i..i + needle.len()] == needle {
            return Some(i);
        }
    }
    None
}

// ---------------------------------------------------------------------------
// Exported functions (called by Marge plugin runtime)
// ---------------------------------------------------------------------------

/// Called once when the plugin is loaded.
/// Sets the initial sensor state to "Loading..." so the entity is visible
/// in the Marge dashboard immediately.
#[no_mangle]
pub extern "C" fn init() {
    log(2, "joke-sensor plugin initializing");
    set_state(ENTITY_ID, "Loading...");
    log(2, "joke-sensor: sensor.joke set to Loading...");
}

/// Called periodically by the plugin manager (default: every 60 seconds).
/// Fetches a random joke from the public API and updates sensor.joke with
/// the setup and punchline concatenated.
#[no_mangle]
pub extern "C" fn poll() {
    log(3, "joke-sensor: poll() called, fetching joke...");

    // Call the host's HTTP GET function.
    // The host reads the URL from our memory, performs the request, and
    // writes the response body into our HTTP_BUF. It returns a packed i64
    // with the status code in the high 32 bits and bytes written in the low 32.
    let result: i64 = unsafe {
        marge_http_get(
            JOKE_API_URL.as_ptr() as i32,
            JOKE_API_URL.len() as i32,
            core::ptr::addr_of!(HTTP_BUF) as i32,
            HTTP_BUF_SIZE as i32,
        )
    };

    // Unpack the result
    let status = (result >> 32) as i32;
    let body_len = (result & 0xFFFFFFFF) as i32;

    if status != 200 {
        log(1, "joke-sensor: HTTP request failed or returned non-200");
        set_state(ENTITY_ID, "Error fetching joke");
        return;
    }

    if body_len <= 0 {
        log(1, "joke-sensor: Empty response body");
        set_state(ENTITY_ID, "Empty response");
        return;
    }

    // Read the response body from our buffer as a UTF-8 string.
    // Use addr_of! to get a raw pointer, then slice it, avoiding a direct
    // reference to the mutable static.
    let body_bytes = unsafe {
        let ptr = core::ptr::addr_of!(HTTP_BUF) as *const u8;
        core::slice::from_raw_parts(ptr, body_len as usize)
    };
    let body = match core::str::from_utf8(body_bytes) {
        Ok(s) => s,
        Err(_) => {
            log(1, "joke-sensor: Response body is not valid UTF-8");
            set_state(ENTITY_ID, "Invalid response");
            return;
        }
    };

    log(3, "joke-sensor: parsing JSON response");

    // Extract the "setup" and "punchline" fields from the JSON response.
    // The API returns: {"type":"general","setup":"...","punchline":"...","id":123}
    let setup = json_extract_string(body, "setup").unwrap_or("(no setup)");
    let punchline = json_extract_string(body, "punchline").unwrap_or("(no punchline)");

    // Build the final joke string: "Setup -- Punchline"
    // We use a fixed buffer to avoid needing an allocator (format!/String
    // require alloc, which adds complexity to no_std-like WASM builds).
    let mut joke_buf = [0u8; 1024];
    let joke_len = build_joke_string(&mut joke_buf, setup, punchline);

    if joke_len == 0 {
        log(1, "joke-sensor: Joke too long for buffer");
        set_state(ENTITY_ID, "Joke too long");
        return;
    }

    // Set the entity state to the joke text.
    let joke_str = unsafe { core::str::from_utf8_unchecked(&joke_buf[..joke_len]) };
    set_state(ENTITY_ID, joke_str);
    log(2, "joke-sensor: updated sensor.joke");
}

/// Concatenate "setup -- punchline" into a fixed-size buffer.
/// Returns the total length written, or 0 if the buffer is too small.
fn build_joke_string(buf: &mut [u8], setup: &str, punchline: &str) -> usize {
    let separator = b" -- ";
    let total = setup.len() + separator.len() + punchline.len();

    if total > buf.len() {
        return 0;
    }

    let mut pos = 0;

    buf[pos..pos + setup.len()].copy_from_slice(setup.as_bytes());
    pos += setup.len();

    buf[pos..pos + separator.len()].copy_from_slice(separator);
    pos += separator.len();

    buf[pos..pos + punchline.len()].copy_from_slice(punchline.as_bytes());
    pos += punchline.len();

    pos
}
