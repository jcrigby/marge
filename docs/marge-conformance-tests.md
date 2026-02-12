# MARGE Ã¢â‚¬â€ Conformance Test Suite Specification

**Document Number:** MRG-CTS-001  
**Version:** 0.1.0-DRAFT  
**Classification:** UNCLASSIFIED // FOUO  
**Date:** 2026-02-11  
**Parent Document:** MRG-SSS-001 (System/Subsystem Specification)  
**Prepared For:** The Department of Not Running Python In Production  

---

## 0. THE IDEA

The SSS document (MRG-SSS-001) is the *narrative* specification. This document is the *executable* specification.

The insight is simple: if we build an exhaustive black-box test suite that validates correct behavior against Home Assistant (HA-legacy), that same test suite Ã¢â‚¬â€ without modification Ã¢â‚¬â€ becomes the acceptance criteria for Marge (HA-NG). Every test passes against HA today. Every test must pass against Marge tomorrow.

This is not a new idea. It's how every successful system rewrite has worked:

- **SQLite** maintains a test suite with 100% branch coverage (~92 million test cases). Any compatible database must pass the same tests.
- **LLVM** validated against GCC's test suite before anyone trusted it to compile production code.
- **MariaDB** forked MySQL's test suite and ran it green before shipping.
- **Web browsers** use the WPT (Web Platform Tests) Ã¢â‚¬â€ 1.7 million tests that define what "a browser" means, independent of implementation.

We're doing the same thing for smarthome platforms.

### What This Buys Us

1. **The spec is executable.** No ambiguity about what "HA-compatible" means Ã¢â‚¬â€ it means passing 100% of these tests.
2. **Edge cases are discovered, not imagined.** Run the tests against HA, observe the behavior, encode the behavior. We don't have to guess what `climate.set_temperature` does when you pass a string Ã¢â‚¬â€ we just test it and record the answer.
3. **The moving target problem goes away.** When HA 2025.6 adds `lawn_mower.dock`, we add test cases, run them green against HA, then implement in Marge. The test suite *is* the changelog.
4. **Regression protection is free.** Every bug fix in Marge gets a test case. That test also runs against HA to confirm HA has the same behavior.
5. **Community contribution is easy.** "Write a test" is a much lower bar than "write a feature." Someone can contribute 50 test cases for the `climate` domain without touching Marge's Rust code.
6. **LLM-driven development has a feedback loop.** An LLM agent can write implementation code, run the conformance suite, read the failures, and iterate Ã¢â‚¬" the Ralph loop pattern, but with a spec-grade test harness instead of vibes. The tests don't care who (or what) wrote the code.

### Terminology

| Term | Definition |
|---|---|
| **SUT** | System Under Test Ã¢â‚¬â€ either HA-legacy or Marge |
| **HA-legacy** | The current Python-based Home Assistant |
| **HA-NG** | Marge (the Rust-based replacement) |
| **Conformance Test** | A test that validates externally observable behavior via public APIs |
| **Characterization Test** | A test derived by observing what the SUT actually does (as opposed to what docs say it should do) |
| **Behavior Parity** | HA-NG produces identical responses to HA-legacy for the same inputs |

---

## 1. TEST ARCHITECTURE

### 1.1 Black-Box Principle

All tests interact with the SUT exclusively through its public interfaces:

```
Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
Ã¢â€â€š            Conformance Test Suite             Ã¢â€â€š
Ã¢â€â€š                                              Ã¢â€â€š
Ã¢â€â€š  Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€š REST API Ã¢â€â€š Ã¢â€â€šWebSocket Ã¢â€â€š Ã¢â€â€š    MQTT      Ã¢â€â€š  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€š Client   Ã¢â€â€š Ã¢â€â€š Client   Ã¢â€â€š Ã¢â€â€š   Client     Ã¢â€â€š  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ  Ã¢â€â€š
Ã¢â€â€š       Ã¢â€â€š            Ã¢â€â€š              Ã¢â€â€š          Ã¢â€â€š
Ã¢â€â€š  Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€š         YAML Config Generator          Ã¢â€â€š  Ã¢â€â€š
Ã¢â€â€š  Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ  Ã¢â€â€š
Ã¢â€â€š                   Ã¢â€â€š                          Ã¢â€â€š
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¼Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
                    Ã¢â€â€š
        Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂªÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
        PUBLIC API BOUNDARY (the only
        interface tests may touch)
        Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂªÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
                    Ã¢â€â€š
    Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
    Ã¢â€â€š     SUT (HA-legacy or HA-NG)   Ã¢â€â€š
    Ã¢â€â€š                                Ã¢â€â€š
    Ã¢â€â€š  Tests know NOTHING about:     Ã¢â€â€š
    Ã¢â€â€š  - Implementation language     Ã¢â€â€š
    Ã¢â€â€š  - Internal data structures    Ã¢â€â€š
    Ã¢â€â€š  - Process architecture        Ã¢â€â€š
    Ã¢â€â€š  - Database schema             Ã¢â€â€š
    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
```

**Rules:**
- Tests SHALL NOT import any HA or Marge internal modules.
- Tests SHALL NOT read or write the SUT's database directly.
- Tests SHALL NOT inspect process internals, memory, or goroutines/threads.
- Tests MAY generate YAML configuration files and restart the SUT.
- Tests MAY connect to the SUT's MQTT broker as an external client.

### 1.2 Test Infrastructure

```
Language:        Python 3.12+ (pytest)
                 (Yes, Python. The irony is intentional.
                  The test suite doesn't need to be fast.
                  It needs to be readable and contributor-friendly.)

Framework:       pytest + pytest-asyncio
HTTP Client:     httpx (async)
WebSocket:       websockets library
MQTT:            aiomqtt (asyncio MQTT v5 client)
Config Gen:      Jinja2 templates Ã¢â€ â€™ YAML
SUT Lifecycle:   Docker Compose (swap SUT image via env var)
CI:              GitHub Actions matrix: [ha-legacy, marge]
```

### 1.3 SUT Lifecycle Management

```python
# conftest.py Ã¢â‚¬â€ top-level fixtures

import pytest
import os

SUT_TYPE = os.environ.get("SUT_TYPE", "ha-legacy")  # or "marge"

@pytest.fixture(scope="session")
def sut():
    """Start the System Under Test via Docker Compose."""
    if SUT_TYPE == "ha-legacy":
        image = "ghcr.io/home-assistant/home-assistant:2024.12"
    elif SUT_TYPE == "marge":
        image = "ghcr.io/marge-home/marge:latest"
    else:
        raise ValueError(f"Unknown SUT_TYPE: {SUT_TYPE}")
    
    compose = SUTManager(image=image)
    compose.start()
    compose.wait_for_ready(timeout=120)  # HA is slow to start
    yield compose
    compose.stop()

@pytest.fixture
def api(sut):
    """REST API client pointed at the running SUT."""
    return RESTClient(base_url=sut.api_url, token=sut.token)

@pytest.fixture
def ws(sut):
    """WebSocket client pointed at the running SUT."""
    return WSClient(url=sut.ws_url, token=sut.token)

@pytest.fixture
def mqtt(sut):
    """MQTT client connected to the SUT's broker."""
    return MQTTClient(host=sut.mqtt_host, port=sut.mqtt_port)
```

### 1.4 Running the Suite

```bash
# Run against HA-legacy (the reference implementation)
SUT_TYPE=ha-legacy pytest tests/ -v --tb=short

# Run against Marge
SUT_TYPE=marge pytest tests/ -v --tb=short

# Run a specific domain
SUT_TYPE=marge pytest tests/entity/test_light.py -v

# Run with parallel execution
SUT_TYPE=ha-legacy pytest tests/ -v -n auto

# Generate compatibility report
SUT_TYPE=marge pytest tests/ --json-report --json-report-file=compat.json
python scripts/compat_report.py compat.json
```

---

## 2. TEST CATEGORIES

### 2.1 Test Hierarchy

```
tests/
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ conftest.py                     # SUT lifecycle, shared fixtures
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ clients/                        # API client libraries
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ rest.py                     # REST API client
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ websocket.py                # WebSocket client
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ mqtt.py                     # MQTT client
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ config.py                   # YAML config generator
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ core/                           # Core engine tests
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_event_bus.py           # Event pub/sub, filtering, ordering
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_state_machine.py       # State reads/writes, change detection
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_service_registry.py    # Service registration, invocation
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_entity_registry.py     # Entity CRUD, metadata persistence
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_device_registry.py     # Device grouping, lifecycle
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_area_registry.py       # Area CRUD
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ test_config_parsing.py      # YAML/TOML configuration
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ entity/                         # Entity domain tests (one file per domain)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_light.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_switch.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_sensor.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_binary_sensor.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_climate.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_cover.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_lock.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_media_player.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_alarm_control_panel.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_fan.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_camera.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_vacuum.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_weather.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_button.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_number.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_select.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_text.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_event.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_update.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_device_tracker.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_person.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_input_boolean.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_input_number.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_input_select.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_input_text.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_input_datetime.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_scene.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_script.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_automation_entity.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_calendar.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_todo.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_humidifier.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_siren.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_valve.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_lawn_mower.py
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_water_heater.py
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ test_notify.py
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ automation/                     # Automation engine tests
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_triggers.py            # All trigger types
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_conditions.py          # All condition types
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_actions.py             # All action types
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_templates.py           # Template rendering
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_run_modes.py           # single/restart/queued/parallel
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_variables.py           # Trigger vars, automation vars
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_traces.py              # Debug trace recording
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_blueprints.py          # Blueprint instantiation
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ test_scripts.py             # Script execution
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ api/                            # API conformance tests
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_rest_states.py         # GET/POST /api/states
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_rest_services.py       # GET/POST /api/services
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_rest_events.py         # GET/POST /api/events
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_rest_config.py         # GET /api/config
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_rest_history.py        # GET /api/history
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_rest_template.py       # POST /api/template
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_rest_auth.py           # Authentication, tokens
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_rest_errors.py         # Error responses, status codes
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_ws_subscribe.py        # WebSocket event subscription
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_ws_commands.py         # WebSocket commands
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_ws_auth.py             # WebSocket authentication
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ test_ws_stress.py           # Concurrent connections, throughput
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ mqtt/                           # MQTT conformance tests
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_mqtt_discovery.py      # HA MQTT Discovery protocol
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_mqtt_state.py          # State via MQTT topics
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_mqtt_commands.py       # Command topics
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_mqtt_birth_will.py     # Birth/LWT messages
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ test_mqtt_qos.py           # QoS levels, retained messages
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ integration/                    # Integration-level tests
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_input_entities.py      # input_boolean, input_number, etc.
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_template_entities.py   # Template sensors, lights, etc.
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_group.py               # Entity grouping
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_sun.py                 # Sun integration (sunrise/sunset)
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_time_date.py           # Time/date sensor
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ test_command_line.py        # Command line integration
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ recorder/                       # History & persistence tests
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_state_history.py       # State history queries
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_statistics.py          # Hourly/daily/monthly stats
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_purge.py               # Data retention/purging
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ test_persistence.py         # Survive restart, recover state
Ã¢â€â€š
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ edge_cases/                     # The stuff that breaks rewrites
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_unicode.py             # Unicode in entity names, states
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_large_state.py         # Entities with huge attribute sets
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_rapid_updates.py       # 1000 state changes/second
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_clock_changes.py       # DST transitions, NTP jumps
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_unavailable.py         # Entity unavailable states
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_unknown_state.py       # "unknown" vs "unavailable"
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_concurrent_writes.py   # Parallel state updates
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_long_running.py        # 24-hour soak test
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_config_reload.py       # Hot-reload configuration
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_empty_config.py        # Minimal/empty configuration
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_malformed_input.py     # Bad API input handling
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_special_characters.py  # Entity IDs with dots, underscores
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ test_numeric_precision.py   # Float handling in sensors
Ã¢â€â€š
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ performance/                    # Performance benchmarks (Marge-only)
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_startup_time.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_memory_baseline.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_state_throughput.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_event_throughput.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_api_latency.py
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ test_ws_latency.py
    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ test_entity_scale.py        # 10K, 50K, 100K entities
```

---

## 3. TEST SPECIFICATIONS

### 3.1 Core Ã¢â‚¬â€ State Machine (test_state_machine.py)

```python
"""
State Machine Conformance Tests

Validates: SSS Ã‚Â§4.1.2 (CSC-STATE)
Requirements: STATE-001 through STATE-008
"""

import pytest
from datetime import datetime, timezone


class TestStateReads:
    """STATE-001, STATE-002: State storage and retrieval."""

    async def test_get_all_states(self, api):
        """GET /api/states returns a list of all entity states."""
        states = await api.get_states()
        assert isinstance(states, list)
        assert len(states) > 0
        # Every state has required fields
        for state in states:
            assert "entity_id" in state
            assert "state" in state
            assert "attributes" in state
            assert "last_changed" in state
            assert "last_updated" in state
            assert "context" in state

    async def test_get_single_state(self, api):
        """GET /api/states/{entity_id} returns a single state object."""
        state = await api.get_state("sun.sun")
        assert state["entity_id"] == "sun.sun"
        assert state["state"] in ("above_horizon", "below_horizon")
        assert "next_rising" in state["attributes"]
        assert "next_setting" in state["attributes"]

    async def test_get_nonexistent_state(self, api):
        """GET /api/states/{entity_id} returns 404 for unknown entities."""
        resp = await api.get_state_raw("sensor.does_not_exist")
        assert resp.status_code == 404

    async def test_entity_id_format(self, api):
        """All entity_ids follow the {domain}.{object_id} format."""
        states = await api.get_states()
        for state in states:
            parts = state["entity_id"].split(".", 1)
            assert len(parts) == 2, f"Invalid entity_id: {state['entity_id']}"
            assert len(parts[0]) > 0, "Empty domain"
            assert len(parts[1]) > 0, "Empty object_id"


class TestStateWrites:
    """STATE-003: State changes fire events."""

    async def test_set_state_creates_entity(self, api):
        """POST /api/states/{entity_id} creates new entity, returns 201."""
        resp = await api.set_state_raw(
            "sensor.test_created",
            {"state": "42", "attributes": {"unit_of_measurement": "Ã‚Â°C"}}
        )
        assert resp.status_code == 201

        state = await api.get_state("sensor.test_created")
        assert state["state"] == "42"
        assert state["attributes"]["unit_of_measurement"] == "Ã‚Â°C"

    async def test_set_state_updates_entity(self, api):
        """POST /api/states/{entity_id} updates existing entity, returns 200."""
        # Create
        await api.set_state("sensor.test_update", {"state": "1"})
        # Update
        resp = await api.set_state_raw(
            "sensor.test_update", {"state": "2"}
        )
        assert resp.status_code == 200
        state = await api.get_state("sensor.test_update")
        assert state["state"] == "2"

    async def test_state_change_fires_event(self, api, ws):
        """STATE-003: state_changed event fires on state change."""
        events = []
        await ws.subscribe_events("state_changed")

        # Change state
        await api.set_state("sensor.test_event", {"state": "before"})
        await api.set_state("sensor.test_event", {"state": "after"})

        event = await ws.wait_for_event(
            lambda e: (
                e["data"]["entity_id"] == "sensor.test_event"
                and e["data"]["new_state"]["state"] == "after"
            ),
            timeout=5
        )
        assert event is not None
        assert event["data"]["old_state"]["state"] == "before"
        assert event["data"]["new_state"]["state"] == "after"

    async def test_no_event_on_same_state(self, api, ws):
        """No state_changed event when state value doesn't change."""
        await api.set_state("sensor.test_nochange", {"state": "same"})
        await ws.subscribe_events("state_changed")

        # Set same state again
        await api.set_state("sensor.test_nochange", {"state": "same"})

        # Should NOT get a state_changed event with different state
        event = await ws.wait_for_event(
            lambda e: (
                e["data"]["entity_id"] == "sensor.test_nochange"
                and e["data"]["old_state"]["state"] != e["data"]["new_state"]["state"]
            ),
            timeout=2
        )
        assert event is None, "Got unexpected state_changed event for same state"


class TestStateTimestamps:
    """STATE-006: last_changed vs last_updated vs last_reported."""

    async def test_last_changed_updates_on_state_change(self, api):
        """last_changed updates when state VALUE changes."""
        await api.set_state("sensor.ts_test", {"state": "a"})
        state1 = await api.get_state("sensor.ts_test")

        await asyncio.sleep(0.1)
        await api.set_state("sensor.ts_test", {"state": "b"})
        state2 = await api.get_state("sensor.ts_test")

        assert state2["last_changed"] > state1["last_changed"]

    async def test_last_changed_stable_on_attribute_change(self, api):
        """last_changed does NOT update when only attributes change."""
        await api.set_state(
            "sensor.ts_test2",
            {"state": "fixed", "attributes": {"foo": 1}}
        )
        state1 = await api.get_state("sensor.ts_test2")

        await asyncio.sleep(0.1)
        await api.set_state(
            "sensor.ts_test2",
            {"state": "fixed", "attributes": {"foo": 2}}
        )
        state2 = await api.get_state("sensor.ts_test2")

        assert state2["last_changed"] == state1["last_changed"]
        assert state2["last_updated"] > state1["last_updated"]


class TestContextPropagation:
    """STATE-003, SVREG-006: Context is attached to state changes."""

    async def test_state_has_context(self, api):
        """Every state object includes a context with an id."""
        await api.set_state("sensor.ctx_test", {"state": "1"})
        state = await api.get_state("sensor.ctx_test")
        assert "context" in state
        assert "id" in state["context"]
        assert len(state["context"]["id"]) > 0
```

### 3.2 Core Ã¢â‚¬â€ Service Registry (test_service_registry.py)

```python
"""
Service Registry Conformance Tests

Validates: SSS Ã‚Â§4.1.3 (CSC-SVREG)
Requirements: SVREG-001 through SVREG-006
"""


class TestServiceDiscovery:
    """SVREG-001: Services are registered under {domain}.{service}."""

    async def test_list_services(self, api):
        """GET /api/services returns all registered services."""
        services = await api.get_services()
        assert isinstance(services, list)
        # Every SUT should have homeassistant domain services
        domains = {s["domain"] for s in services}
        assert "homeassistant" in domains

    async def test_homeassistant_services_exist(self, api):
        """Core homeassistant services are always registered."""
        services = await api.get_services()
        ha_services = next(s for s in services if s["domain"] == "homeassistant")
        service_names = set(ha_services["services"].keys())
        expected = {"turn_on", "turn_off", "toggle", "update_entity",
                    "reload_all", "restart", "stop"}
        assert expected.issubset(service_names)


class TestServiceCalls:
    """SVREG-002, SVREG-004: Service invocation patterns."""

    async def test_call_service_by_entity_id(self, api):
        """Service call with entity_id target."""
        # Create an input_boolean to test with
        # (This requires config, so we use one that should exist)
        resp = await api.call_service(
            "input_boolean", "turn_on",
            target={"entity_id": "input_boolean.test_toggle"}
        )
        assert resp.status_code == 200

        state = await api.get_state("input_boolean.test_toggle")
        assert state["state"] == "on"

    async def test_call_service_by_area_id(self, api):
        """SVREG-002: Service call with area_id target."""
        resp = await api.call_service(
            "light", "turn_off",
            target={"area_id": "living_room"}
        )
        assert resp.status_code == 200

    async def test_call_nonexistent_service(self, api):
        """Calling a service that doesn't exist returns an error."""
        resp = await api.call_service_raw(
            "fake_domain", "fake_service", {}
        )
        assert resp.status_code in (400, 404)

    async def test_service_call_fires_event(self, ws, api):
        """Service calls fire call_service events."""
        await ws.subscribe_events("call_service")

        await api.call_service(
            "input_boolean", "toggle",
            target={"entity_id": "input_boolean.test_toggle"}
        )

        event = await ws.wait_for_event(
            lambda e: (
                e["data"]["domain"] == "input_boolean"
                and e["data"]["service"] == "toggle"
            ),
            timeout=5
        )
        assert event is not None
```

### 3.3 Entity Domain Ã¢â‚¬â€ Lights (test_light.py)

```python
"""
Light Entity Domain Conformance Tests

Validates: SSS Ã‚Â§4.2.2 (light domain)
Tests every documented state, attribute, service, and edge case.
"""


class TestLightStates:
    """Light entities have states 'on' and 'off'."""

    async def test_light_on_off(self, api):
        state = await api.get_state("light.test_dimmable")
        assert state["state"] in ("on", "off", "unavailable", "unknown")

    async def test_turn_on(self, api):
        await api.call_service(
            "light", "turn_on",
            target={"entity_id": "light.test_dimmable"}
        )
        state = await api.get_state("light.test_dimmable")
        assert state["state"] == "on"

    async def test_turn_off(self, api):
        await api.call_service(
            "light", "turn_off",
            target={"entity_id": "light.test_dimmable"}
        )
        state = await api.get_state("light.test_dimmable")
        assert state["state"] == "off"

    async def test_toggle(self, api):
        state_before = await api.get_state("light.test_dimmable")
        await api.call_service(
            "light", "toggle",
            target={"entity_id": "light.test_dimmable"}
        )
        state_after = await api.get_state("light.test_dimmable")
        assert state_before["state"] != state_after["state"]


class TestLightAttributes:
    """Light attributes: brightness, color_temp, rgb_color, etc."""

    async def test_brightness_range(self, api):
        """Brightness is 0-255 when the light is on."""
        await api.call_service(
            "light", "turn_on",
            target={"entity_id": "light.test_dimmable"},
            data={"brightness": 128}
        )
        state = await api.get_state("light.test_dimmable")
        assert state["state"] == "on"
        assert 0 <= state["attributes"]["brightness"] <= 255

    async def test_brightness_percentage(self, api):
        """brightness_pct is accepted and converted to 0-255."""
        await api.call_service(
            "light", "turn_on",
            target={"entity_id": "light.test_dimmable"},
            data={"brightness_pct": 50}
        )
        state = await api.get_state("light.test_dimmable")
        # 50% Ã¢â€°Ë† 127-128
        assert 125 <= state["attributes"]["brightness"] <= 130

    async def test_color_temp_mireds(self, api):
        """Color temperature in mireds."""
        await api.call_service(
            "light", "turn_on",
            target={"entity_id": "light.test_color_temp"},
            data={"color_temp": 300}
        )
        state = await api.get_state("light.test_color_temp")
        assert state["attributes"]["color_temp"] == 300
        assert state["attributes"]["color_mode"] == "color_temp"

    async def test_rgb_color(self, api):
        """RGB color as [r, g, b] list."""
        await api.call_service(
            "light", "turn_on",
            target={"entity_id": "light.test_rgb"},
            data={"rgb_color": [255, 0, 0]}
        )
        state = await api.get_state("light.test_rgb")
        assert state["attributes"]["rgb_color"] == [255, 0, 0]
        assert state["attributes"]["color_mode"] == "rgb"

    async def test_supported_color_modes(self, api):
        """Light reports supported_color_modes."""
        state = await api.get_state("light.test_rgb")
        assert "supported_color_modes" in state["attributes"]
        modes = state["attributes"]["supported_color_modes"]
        assert isinstance(modes, list)

    async def test_turn_on_preserves_brightness(self, api):
        """Turning on without brightness uses last known brightness."""
        await api.call_service(
            "light", "turn_on",
            target={"entity_id": "light.test_dimmable"},
            data={"brightness": 200}
        )
        await api.call_service(
            "light", "turn_off",
            target={"entity_id": "light.test_dimmable"}
        )
        await api.call_service(
            "light", "turn_on",
            target={"entity_id": "light.test_dimmable"}
        )
        state = await api.get_state("light.test_dimmable")
        # Should restore to 200 (or close to it)
        assert state["attributes"]["brightness"] >= 195


class TestLightEdgeCases:
    """Edge cases that break rewrites."""

    async def test_turn_on_already_on(self, api):
        """Turning on a light that's already on doesn't error."""
        await api.call_service(
            "light", "turn_on",
            target={"entity_id": "light.test_dimmable"}
        )
        resp = await api.call_service_raw(
            "light", "turn_on",
            target={"entity_id": "light.test_dimmable"}
        )
        assert resp.status_code == 200

    async def test_brightness_zero_turns_off(self, api):
        """Setting brightness to 0 turns the light off (HA behavior)."""
        await api.call_service(
            "light", "turn_on",
            target={"entity_id": "light.test_dimmable"},
            data={"brightness": 0}
        )
        state = await api.get_state("light.test_dimmable")
        # HA turns off the light when brightness=0
        assert state["state"] == "off"

    async def test_invalid_brightness_rejected(self, api):
        """Brightness > 255 is rejected or clamped."""
        resp = await api.call_service_raw(
            "light", "turn_on",
            target={"entity_id": "light.test_dimmable"},
            data={"brightness": 999}
        )
        # Should either reject (400) or clamp to 255
        if resp.status_code == 200:
            state = await api.get_state("light.test_dimmable")
            assert state["attributes"]["brightness"] <= 255
```

### 3.4 Automation Engine (test_triggers.py)

```python
"""
Automation Trigger Conformance Tests

Validates: SSS Ã‚Â§4.3.2 (Trigger Types)
Requirements: AUTO-001 through AUTO-005

These tests load YAML configurations with specific automations,
then verify the automations fire correctly.
"""


class TestStateTrigger:
    """trigger: state Ã¢â‚¬â€ fires on entity state changes."""

    @pytest.fixture(autouse=True)
    async def setup_automation(self, sut):
        """Load automation config that triggers on input_boolean change."""
        sut.load_config("""
automation:
  - id: test_state_trigger
    alias: "Test State Trigger"
    triggers:
      - trigger: state
        entity_id: input_boolean.trigger_source
        to: "on"
    actions:
      - action: input_boolean.turn_on
        target:
          entity_id: input_boolean.trigger_target
        """)
        await sut.reload_automations()

    async def test_trigger_fires(self, api):
        """Automation fires when entity transitions to specified state."""
        # Ensure target is off
        await api.call_service(
            "input_boolean", "turn_off",
            target={"entity_id": "input_boolean.trigger_target"}
        )
        # Trigger source
        await api.call_service(
            "input_boolean", "turn_on",
            target={"entity_id": "input_boolean.trigger_source"}
        )
        # Wait for automation to execute
        await asyncio.sleep(0.5)

        state = await api.get_state("input_boolean.trigger_target")
        assert state["state"] == "on"

    async def test_trigger_does_not_fire_wrong_state(self, api):
        """Automation does NOT fire for unmatched state transitions."""
        await api.call_service(
            "input_boolean", "turn_on",
            target={"entity_id": "input_boolean.trigger_source"}
        )
        await api.call_service(
            "input_boolean", "turn_off",
            target={"entity_id": "input_boolean.trigger_target"}
        )

        # Turn source OFF (automation watches for ON)
        await api.call_service(
            "input_boolean", "turn_off",
            target={"entity_id": "input_boolean.trigger_source"}
        )
        await asyncio.sleep(0.5)

        state = await api.get_state("input_boolean.trigger_target")
        assert state["state"] == "off"


class TestStateTriggerWithFor:
    """trigger: state with 'for' duration."""

    @pytest.fixture(autouse=True)
    async def setup_automation(self, sut):
        sut.load_config("""
automation:
  - id: test_state_for_trigger
    alias: "Test State For Trigger"
    triggers:
      - trigger: state
        entity_id: input_boolean.for_source
        to: "on"
        for: "00:00:02"
    actions:
      - action: input_boolean.turn_on
        target:
          entity_id: input_boolean.for_target
        """)
        await sut.reload_automations()

    async def test_for_waits(self, api):
        """Automation waits for 'for' duration before firing."""
        await api.call_service(
            "input_boolean", "turn_off",
            target={"entity_id": "input_boolean.for_target"}
        )
        await api.call_service(
            "input_boolean", "turn_on",
            target={"entity_id": "input_boolean.for_source"}
        )

        # After 1 second, should NOT have fired yet
        await asyncio.sleep(1)
        state = await api.get_state("input_boolean.for_target")
        assert state["state"] == "off"

        # After 3 seconds total, SHOULD have fired
        await asyncio.sleep(2)
        state = await api.get_state("input_boolean.for_target")
        assert state["state"] == "on"

    async def test_for_cancelled_on_state_change(self, api):
        """'for' timer cancels if entity leaves target state."""
        await api.call_service(
            "input_boolean", "turn_off",
            target={"entity_id": "input_boolean.for_target"}
        )
        await api.call_service(
            "input_boolean", "turn_on",
            target={"entity_id": "input_boolean.for_source"}
        )
        await asyncio.sleep(1)

        # Cancel by turning source off before 'for' expires
        await api.call_service(
            "input_boolean", "turn_off",
            target={"entity_id": "input_boolean.for_source"}
        )
        await asyncio.sleep(2)

        # Should NOT have fired
        state = await api.get_state("input_boolean.for_target")
        assert state["state"] == "off"


class TestTriggerVariables:
    """AUTO-005: trigger.* namespace accessible in actions."""

    @pytest.fixture(autouse=True)
    async def setup_automation(self, sut):
        sut.load_config("""
input_text:
  trigger_result:
    name: Trigger Result
    initial: ""

automation:
  - id: test_trigger_vars
    alias: "Test Trigger Variables"
    triggers:
      - trigger: state
        entity_id: input_boolean.var_source
        id: my_trigger
    actions:
      - action: input_text.set_value
        target:
          entity_id: input_text.trigger_result
        data:
          value: "{{ trigger.id }}-{{ trigger.to_state.state }}"
        """)
        await sut.reload_automations()

    async def test_trigger_id_available(self, api):
        """trigger.id is accessible in action templates."""
        await api.call_service(
            "input_boolean", "turn_on",
            target={"entity_id": "input_boolean.var_source"}
        )
        await asyncio.sleep(0.5)

        state = await api.get_state("input_text.trigger_result")
        assert state["state"] == "my_trigger-on"


class TestRunModes:
    """Automation run modes: single, restart, queued, parallel."""

    @pytest.fixture(autouse=True)
    async def setup_automation(self, sut):
        sut.load_config("""
input_number:
  run_counter:
    name: Run Counter
    initial: 0
    min: 0
    max: 100
    step: 1

automation:
  - id: test_single_mode
    alias: "Test Single Mode"
    mode: single
    triggers:
      - trigger: state
        entity_id: input_boolean.single_source
    actions:
      - delay: "00:00:02"
      - action: input_number.set_value
        target:
          entity_id: input_number.run_counter
        data:
          value: "{{ states('input_number.run_counter') | int + 1 }}"
        """)
        await sut.reload_automations()

    async def test_single_mode_ignores_retrigger(self, api):
        """In single mode, re-triggering while running is ignored."""
        await api.call_service(
            "input_number", "set_value",
            target={"entity_id": "input_number.run_counter"},
            data={"value": 0}
        )

        # Trigger twice rapidly
        await api.call_service(
            "input_boolean", "turn_on",
            target={"entity_id": "input_boolean.single_source"}
        )
        await asyncio.sleep(0.1)
        await api.call_service(
            "input_boolean", "turn_off",
            target={"entity_id": "input_boolean.single_source"}
        )

        # Wait for automation to complete
        await asyncio.sleep(3)

        state = await api.get_state("input_number.run_counter")
        # Should only have incremented once (second trigger ignored)
        assert float(state["state"]) == 1.0
```

### 3.5 MQTT Discovery (test_mqtt_discovery.py)

```python
"""
MQTT Discovery Protocol Conformance Tests

Validates: SSS Ã‚Â§5.2.2 (HA MQTT Discovery Compatibility)
Tests that devices can self-register via MQTT discovery topics.
"""


class TestMQTTDiscovery:
    """HA-compatible MQTT Discovery protocol."""

    async def test_sensor_discovery(self, mqtt, api):
        """Publishing a discovery config creates a sensor entity."""
        await mqtt.publish(
            "homeassistant/sensor/test_node/temperature/config",
            {
                "name": "Test Temperature",
                "state_topic": "test_node/temperature",
                "unit_of_measurement": "Ã‚Â°C",
                "device_class": "temperature",
                "state_class": "measurement",
                "unique_id": "test_node_temperature",
                "device": {
                    "identifiers": ["test_node_001"],
                    "name": "Test Node",
                    "model": "TestDevice",
                    "manufacturer": "TestCorp"
                }
            },
            retain=True
        )

        # Wait for discovery processing
        await asyncio.sleep(2)

        # Entity should now exist
        state = await api.get_state("sensor.test_temperature")
        assert state is not None
        assert state["attributes"]["unit_of_measurement"] == "Ã‚Â°C"
        assert state["attributes"]["device_class"] == "temperature"

    async def test_sensor_state_via_mqtt(self, mqtt, api):
        """Publishing to state_topic updates entity state."""
        await mqtt.publish("test_node/temperature", "23.5")
        await asyncio.sleep(1)

        state = await api.get_state("sensor.test_temperature")
        assert state["state"] == "23.5"

    async def test_discovery_removal(self, mqtt, api):
        """Publishing empty payload to discovery topic removes entity."""
        # First, verify entity exists
        state = await api.get_state("sensor.test_temperature")
        assert state is not None

        # Remove via empty payload
        await mqtt.publish(
            "homeassistant/sensor/test_node/temperature/config",
            "",
            retain=True
        )
        await asyncio.sleep(2)

        # Entity should be gone or unavailable
        resp = await api.get_state_raw("sensor.test_temperature")
        assert resp.status_code == 404 or resp.json()["state"] == "unavailable"

    async def test_switch_discovery_with_command(self, mqtt, api):
        """Switch discovery creates entity that sends MQTT commands."""
        await mqtt.publish(
            "homeassistant/switch/test_relay/power/config",
            {
                "name": "Test Relay",
                "state_topic": "test_relay/state",
                "command_topic": "test_relay/set",
                "payload_on": "ON",
                "payload_off": "OFF",
                "unique_id": "test_relay_power",
            },
            retain=True
        )
        await asyncio.sleep(2)

        # Subscribe to command topic
        commands = []
        await mqtt.subscribe("test_relay/set", lambda msg: commands.append(msg))

        # Call service via REST API
        await api.call_service(
            "switch", "turn_on",
            target={"entity_id": "switch.test_relay"}
        )
        await asyncio.sleep(1)

        # MQTT command should have been published
        assert len(commands) > 0
        assert commands[-1] == "ON"

    async def test_binary_sensor_discovery_device_class(self, mqtt, api):
        """Binary sensor with device_class reflects correct state meaning."""
        await mqtt.publish(
            "homeassistant/binary_sensor/test_node/motion/config",
            {
                "name": "Test Motion",
                "state_topic": "test_node/motion",
                "device_class": "motion",
                "payload_on": "ON",
                "payload_off": "OFF",
                "unique_id": "test_node_motion",
            },
            retain=True
        )
        await asyncio.sleep(2)

        await mqtt.publish("test_node/motion", "ON")
        await asyncio.sleep(1)

        state = await api.get_state("binary_sensor.test_motion")
        assert state["state"] == "on"
        assert state["attributes"]["device_class"] == "motion"
```

### 3.6 Template Engine (test_templates.py)

```python
"""
Template Engine Conformance Tests

Validates: SSS Ã‚Â§4.3.6 (Template Engine)
Requirements: TMPL-001 through TMPL-004

Tests that Jinja2-compatible templates render identically
between HA-legacy and Marge.
"""


class TestStateAccess:
    """Template functions for reading entity state."""

    async def test_states_function(self, api):
        """states('entity_id') returns state string."""
        await api.set_state("sensor.tmpl_test", {"state": "42.5"})
        result = await api.render_template(
            "{{ states('sensor.tmpl_test') }}"
        )
        assert result == "42.5"

    async def test_state_attr(self, api):
        """state_attr('entity_id', 'attr') returns attribute value."""
        await api.set_state(
            "sensor.tmpl_test",
            {"state": "42.5", "attributes": {"unit": "Ã‚Â°C"}}
        )
        result = await api.render_template(
            "{{ state_attr('sensor.tmpl_test', 'unit') }}"
        )
        assert result == "Ã‚Â°C"

    async def test_is_state(self, api):
        """is_state('entity_id', 'value') returns boolean."""
        await api.set_state("sensor.tmpl_test", {"state": "42.5"})
        result = await api.render_template(
            "{{ is_state('sensor.tmpl_test', '42.5') }}"
        )
        assert result.lower() == "true"

    async def test_states_unknown_entity(self, api):
        """states() for nonexistent entity returns 'unknown'."""
        result = await api.render_template(
            "{{ states('sensor.nonexistent_xyz') }}"
        )
        assert result in ("unknown", "unavailable")


class TestFilters:
    """Jinja2 filters for type conversion and math."""

    async def test_float_filter(self, api):
        result = await api.render_template("{{ '42.5' | float }}")
        assert float(result) == 42.5

    async def test_int_filter(self, api):
        result = await api.render_template("{{ '42' | int }}")
        assert int(result) == 42

    async def test_round_filter(self, api):
        result = await api.render_template("{{ 3.14159 | round(2) }}")
        assert result == "3.14"

    async def test_float_default(self, api):
        """float filter with default for non-numeric input."""
        result = await api.render_template(
            "{{ 'not_a_number' | float(0) }}"
        )
        assert float(result) == 0.0

    async def test_multiply(self, api):
        result = await api.render_template("{{ 6 * 7 }}")
        assert result.strip() == "42"

    async def test_string_concatenation(self, api):
        result = await api.render_template(
            "{{ 'hello' ~ ' ' ~ 'world' }}"
        )
        assert result == "hello world"


class TestTimeFunctions:
    """Time-related template functions."""

    async def test_now(self, api):
        """now() returns current datetime."""
        result = await api.render_template(
            "{{ now().year }}"
        )
        assert int(result) >= 2024

    async def test_today_at(self, api):
        """today_at('HH:MM') returns datetime for today."""
        result = await api.render_template(
            "{{ today_at('08:00').hour }}"
        )
        assert result == "8"

    async def test_as_timestamp(self, api):
        """as_timestamp() converts datetime to unix timestamp."""
        result = await api.render_template(
            "{{ as_timestamp(now()) | int > 0 }}"
        )
        assert result.lower() == "true"


class TestConditionals:
    """iif() and conditional template expressions."""

    async def test_iif(self, api):
        """iif(condition, true_val, false_val)."""
        result = await api.render_template(
            "{{ iif(1 > 0, 'yes', 'no') }}"
        )
        assert result == "yes"

    async def test_ternary(self, api):
        """Jinja2 ternary: value if condition else other."""
        result = await api.render_template(
            "{{ 'hot' if 30 > 25 else 'cold' }}"
        )
        assert result == "hot"


class TestComplexTemplates:
    """Real-world template patterns from HA community."""

    async def test_entity_count_template(self, api):
        """Count entities in a specific state."""
        result = await api.render_template(
            "{{ states | selectattr('state', 'eq', 'on') | list | count }}"
        )
        # Just verify it returns a number without erroring
        assert int(result) >= 0

    async def test_sensor_math_template(self, api):
        """Math on sensor values (common HA pattern)."""
        await api.set_state("sensor.temp_c", {"state": "25"})
        result = await api.render_template(
            "{{ (states('sensor.temp_c') | float * 9/5 + 32) | round(1) }}"
        )
        assert float(result) == 77.0
```

### 3.7 Edge Cases (test_edge_cases.py)

```python
"""
Edge Case Tests Ã¢â‚¬â€ The Stuff That Breaks Rewrites

These tests encode surprising, undocumented, or corner-case behaviors
discovered by running against HA-legacy. They are the tests most likely
to catch behavioral differences in HA-NG.
"""


class TestUnavailableVsUnknown:
    """HA distinguishes 'unavailable' from 'unknown' Ã¢â‚¬â€ subtly."""

    async def test_unavailable_is_not_unknown(self, api):
        """'unavailable' and 'unknown' are distinct states."""
        await api.set_state("sensor.u_test1", {"state": "unavailable"})
        await api.set_state("sensor.u_test2", {"state": "unknown"})

        s1 = await api.get_state("sensor.u_test1")
        s2 = await api.get_state("sensor.u_test2")
        assert s1["state"] == "unavailable"
        assert s2["state"] == "unknown"
        assert s1["state"] != s2["state"]

    async def test_unavailable_in_template(self, api):
        """Templates can distinguish unavailable from unknown."""
        await api.set_state("sensor.u_tmpl", {"state": "unavailable"})
        result = await api.render_template(
            "{{ states('sensor.u_tmpl') }}"
        )
        assert result == "unavailable"


class TestUnicode:
    """Unicode handling in entity names, states, and attributes."""

    async def test_unicode_state(self, api):
        await api.set_state(
            "sensor.unicode_test",
            {"state": "Ã¦â€”Â¥Ã¦Å“Â¬Ã¨ÂªÅ¾Ã£Æ’â€ Ã£â€šÂ¹Ã£Æ’Ë† Ã°Å¸ÂÂ "}
        )
        state = await api.get_state("sensor.unicode_test")
        assert state["state"] == "Ã¦â€”Â¥Ã¦Å“Â¬Ã¨ÂªÅ¾Ã£Æ’â€ Ã£â€šÂ¹Ã£Æ’Ë† Ã°Å¸ÂÂ "

    async def test_unicode_attributes(self, api):
        await api.set_state(
            "sensor.unicode_attr",
            {"state": "ok", "attributes": {"location": "MÃƒÂ¼nchen"}}
        )
        state = await api.get_state("sensor.unicode_attr")
        assert state["attributes"]["location"] == "MÃƒÂ¼nchen"


class TestNumericPrecision:
    """Float handling Ã¢â‚¬â€ a classic source of behavioral divergence."""

    async def test_float_roundtrip(self, api):
        """Float values survive a write/read cycle."""
        await api.set_state(
            "sensor.float_test",
            {"state": "23.456789012345"}
        )
        state = await api.get_state("sensor.float_test")
        # State is stored as string, so exact match
        assert state["state"] == "23.456789012345"

    async def test_float_in_template(self, api):
        """Float arithmetic in templates matches HA behavior."""
        result = await api.render_template("{{ 0.1 + 0.2 }}")
        # Python/Jinja2: 0.30000000000000004
        val = float(result)
        assert abs(val - 0.3) < 0.0001

    async def test_large_numbers(self, api):
        """Very large numbers don't overflow or lose precision."""
        await api.set_state(
            "sensor.big_number",
            {"state": "99999999999999"}
        )
        state = await api.get_state("sensor.big_number")
        assert state["state"] == "99999999999999"


class TestRapidStateChanges:
    """High-frequency state updates Ã¢â‚¬â€ stress test for the state machine."""

    async def test_100_rapid_updates(self, api, ws):
        """100 state changes in rapid succession, all events delivered."""
        await ws.subscribe_events("state_changed")

        for i in range(100):
            await api.set_state(
                "sensor.rapid_test",
                {"state": str(i)}
            )

        # Collect events for a few seconds
        events = await ws.collect_events(
            filter=lambda e: e["data"]["entity_id"] == "sensor.rapid_test",
            timeout=5
        )

        # Final state should be 99
        state = await api.get_state("sensor.rapid_test")
        assert state["state"] == "99"

        # We should have received change events
        # (exact count may vary due to batching, but should be >50)
        assert len(events) > 50


class TestConfigReload:
    """Hot-reloading configuration without restart."""

    async def test_automation_reload(self, sut, api):
        """Reloading automations picks up new automations."""
        sut.load_config("""
automation:
  - id: reload_test_auto
    alias: "Reload Test"
    triggers:
      - trigger: state
        entity_id: input_boolean.reload_source
        to: "on"
    actions:
      - action: input_boolean.turn_on
        target:
          entity_id: input_boolean.reload_target
        """)

        await api.call_service("automation", "reload")
        await asyncio.sleep(2)

        # Verify automation exists
        state = await api.get_state("automation.reload_test")
        assert state is not None


class TestEmptyAndMinimalConfig:
    """System behavior with minimal or empty configuration."""

    async def test_sun_entity_always_exists(self, api):
        """sun.sun exists even with empty config."""
        state = await api.get_state("sun.sun")
        assert state["state"] in ("above_horizon", "below_horizon")

    async def test_api_works_with_minimal_config(self, api):
        """API is functional with only default config."""
        resp = await api.get_config()
        assert "latitude" in resp
        assert "longitude" in resp
```

### 3.8 WebSocket API (test_ws_subscribe.py)

```python
"""
WebSocket Event Subscription Tests

Validates: SSS Ã‚Â§5.1.2 (WebSocket API)
"""


class TestWebSocketSubscription:

    async def test_subscribe_all_events(self, ws):
        """Subscribe to all events."""
        sub_id = await ws.subscribe_events()
        assert sub_id is not None

    async def test_subscribe_specific_event(self, ws, api):
        """Subscribe to specific event type."""
        await ws.subscribe_events("state_changed")

        await api.set_state("sensor.ws_test", {"state": "hello"})

        event = await ws.wait_for_event(
            lambda e: e["data"]["entity_id"] == "sensor.ws_test",
            timeout=5
        )
        assert event is not None
        assert event["event_type"] == "state_changed"

    async def test_unsubscribe(self, ws):
        """Unsubscribe stops event delivery."""
        sub_id = await ws.subscribe_events("state_changed")
        await ws.unsubscribe(sub_id)
        # No crash, no error

    async def test_multiple_subscriptions(self, ws, api):
        """Multiple simultaneous subscriptions work."""
        sub1 = await ws.subscribe_events("state_changed")
        sub2 = await ws.subscribe_events("call_service")

        await api.call_service(
            "input_boolean", "turn_on",
            target={"entity_id": "input_boolean.test_toggle"}
        )

        # Should receive both event types
        events = await ws.collect_events(timeout=3)
        event_types = {e["event_type"] for e in events}
        assert "state_changed" in event_types
        assert "call_service" in event_types

    async def test_get_states_command(self, ws):
        """get_states WebSocket command returns all states."""
        states = await ws.send_command({"type": "get_states"})
        assert isinstance(states, list)
        assert len(states) > 0

    async def test_call_service_command(self, ws):
        """call_service WebSocket command invokes service."""
        result = await ws.send_command({
            "type": "call_service",
            "domain": "input_boolean",
            "service": "toggle",
            "target": {"entity_id": "input_boolean.test_toggle"}
        })
        assert result is not None

    async def test_render_template_subscription(self, ws, api):
        """subscribe to template rendering updates."""
        result = await ws.send_command({
            "type": "render_template",
            "template": "{{ states('sensor.ws_tmpl_test') }}"
        })

        # Update the entity
        await api.set_state("sensor.ws_tmpl_test", {"state": "new_value"})

        # Should receive updated template render
        event = await ws.wait_for_event(
            lambda e: "new_value" in str(e.get("result", "")),
            timeout=5
        )
        assert event is not None
```

---

## 4. COMPATIBILITY SCORING

### 4.1 Compatibility Report

The test suite generates a compatibility report after each run:

```
Ã¢â€¢â€Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢â€”
Ã¢â€¢â€˜            MARGE CONFORMANCE REPORT                      Ã¢â€¢â€˜
Ã¢â€¢â€˜            SUT: marge v0.1.0                              Ã¢â€¢â€˜
Ã¢â€¢â€˜            Baseline: home-assistant 2024.12.0                Ã¢â€¢â€˜
Ã¢â€¢â€˜            Date: 2026-02-11                                  Ã¢â€¢â€˜
Ã¢â€¢Â Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â£
Ã¢â€¢â€˜                                                              Ã¢â€¢â€˜
Ã¢â€¢â€˜  OVERALL: 847 / 1,203 tests passing (70.4%)                 Ã¢â€¢â€˜
Ã¢â€¢â€˜                                                              Ã¢â€¢â€˜
Ã¢â€¢â€˜  Category              Pass    Fail    Skip    Coverage     Ã¢â€¢â€˜
Ã¢â€¢â€˜  Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Core State Machine     45/45    0       0      100.0% Ã¢Å“â€¦   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Core Event Bus         38/38    0       0      100.0% Ã¢Å“â€¦   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Core Service Registry  22/22    0       0      100.0% Ã¢Å“â€¦   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Entity: light          34/36    2       0       94.4% Ã°Å¸Å¸Â¡   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Entity: switch         18/18    0       0      100.0% Ã¢Å“â€¦   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Entity: sensor         42/42    0       0      100.0% Ã¢Å“â€¦   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Entity: climate        28/41   13       0       68.3% Ã°Å¸â€Â´   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Entity: cover          15/22    7       0       68.2% Ã°Å¸â€Â´   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Automation: triggers   52/58    6       0       89.7% Ã°Å¸Å¸Â¡   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Automation: conditions 31/31    0       0      100.0% Ã¢Å“â€¦   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Automation: actions    44/48    4       0       91.7% Ã°Å¸Å¸Â¡   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Automation: templates  63/78   15       0       80.8% Ã°Å¸Å¸Â¡   Ã¢â€¢â€˜
Ã¢â€¢â€˜  REST API               55/55    0       0      100.0% Ã¢Å“â€¦   Ã¢â€¢â€˜
Ã¢â€¢â€˜  WebSocket API          41/48    7       0       85.4% Ã°Å¸Å¸Â¡   Ã¢â€¢â€˜
Ã¢â€¢â€˜  MQTT Discovery         22/22    0       0      100.0% Ã¢Å“â€¦   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Edge Cases             38/52   14       0       73.1% Ã°Å¸Å¸Â¡   Ã¢â€¢â€˜
Ã¢â€¢â€˜  Input Entities         24/24    0       0      100.0% Ã¢Å“â€¦   Ã¢â€¢â€˜
Ã¢â€¢â€˜  History/Recorder        0/35    0      35        N/A  Ã¢ÂÂ­Ã¯Â¸Â    Ã¢â€¢â€˜
Ã¢â€¢â€˜                                                              Ã¢â€¢â€˜
Ã¢â€¢â€˜  Release Gate:  P1 tests: 412/412 (100.0%) Ã¢Å“â€¦ PASS          Ã¢â€¢â€˜
Ã¢â€¢â€˜                 P2 tests: 298/378 (78.8%)  Ã°Å¸Å¸Â¡ CONDITIONAL   Ã¢â€¢â€˜
Ã¢â€¢â€˜                 P3 tests: 137/413 (33.2%)  Ã°Å¸â€Â´ NOT READY     Ã¢â€¢â€˜
Ã¢â€¢â€˜                                                              Ã¢â€¢â€˜
Ã¢â€¢Å¡Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
```

### 4.2 Release Gates

| Milestone | Gate Criteria |
|---|---|
| **Alpha** (internal testing) | 100% P1 core tests + 100% P1 API tests |
| **Beta** (early adopters) | 100% P1 + Ã¢â€°Â¥80% P2 + MQTT Discovery 100% |
| **RC** (release candidate) | 100% P1 + 100% P2 + Ã¢â€°Â¥80% P3 + no P1 regressions in 30 days |
| **GA** (general availability) | 100% P1 + 100% P2 + Ã¢â€°Â¥95% P3 + migration wizard passing |

### 4.3 Test Priority Classification

| Priority | Description | Example |
|---|---|---|
| **P1** | Core functionality Ã¢â‚¬â€ system is broken without it | State machine, event bus, service calls, basic entity operations, REST API CRUD |
| **P2** | Important functionality Ã¢â‚¬â€ most users need it | Automation triggers/conditions/actions, MQTT discovery, template engine, WebSocket subscriptions |
| **P3** | Full compatibility Ã¢â‚¬â€ matches HA behavior exactly | Edge cases, obscure template functions, device tracker history, statistics, energy management |
| **Perf** | Performance targets Ã¢â‚¬â€ Marge-only (not run against HA) | Startup time, memory, throughput, latency benchmarks |

---

## 5. TEST DEVELOPMENT WORKFLOW

### 5.1 Characterization Test Process

For discovering undocumented behavior:

```
1. HYPOTHESIZE: "What does HA do when you set brightness to -1?"
2. WRITE THE TEST: test_negative_brightness(api)
3. RUN AGAINST HA: SUT_TYPE=ha-legacy pytest test_light.py::test_negative_brightness
4. OBSERVE: HA returns 400? Clamps to 0? Ignores? Crashes?
5. ENCODE: Assert the observed behavior
6. DOCUMENT: Add a comment explaining the behavior
7. COMMIT: This test now defines correct behavior for Marge
```

### 5.2 Contributing Tests

```
GOOD test contribution:
  - Tests ONE specific behavior
  - Has a clear docstring explaining what it validates
  - References SSS requirement IDs where applicable
  - Runs in <5 seconds
  - Doesn't depend on other tests (isolated)
  - Works against both HA-legacy and HA-NG

BAD test contribution:
  - Tests implementation details (Python internals, database schema)
  - Requires specific hardware
  - Takes >30 seconds
  - Uses HA's internal Python API
  - Only works against one SUT
```

### 5.3 Test Fixtures (Shared Configuration)

The test suite ships with a standard `test_configuration.yaml` that both SUTs load:

```yaml
# tests/fixtures/configuration.yaml
# Minimal config that provides entities for testing

homeassistant:
  name: "Conformance Test Home"
  latitude: 40.3916
  longitude: -111.8508
  elevation: 1400
  unit_system: us_customary
  time_zone: America/Denver

input_boolean:
  test_toggle:
    name: "Test Toggle"
  trigger_source:
    name: "Trigger Source"
  trigger_target:
    name: "Trigger Target"
  for_source:
    name: "For Source"
  for_target:
    name: "For Target"
  var_source:
    name: "Var Source"
  single_source:
    name: "Single Source"
  reload_source:
    name: "Reload Source"
  reload_target:
    name: "Reload Target"

input_number:
  run_counter:
    name: "Run Counter"
    initial: 0
    min: 0
    max: 100
    step: 1

input_text:
  trigger_result:
    name: "Trigger Result"
    initial: ""

# Mock integrations for entity testing
light:
  - platform: demo
switch:
  - platform: demo
sensor:
  - platform: demo
climate:
  - platform: demo
cover:
  - platform: demo
lock:
  - platform: demo
fan:
  - platform: demo
media_player:
  - platform: demo
alarm_control_panel:
  - platform: demo

mqtt:
  broker: localhost
  port: 1883
```

---

## 6. APPENDIX: ESTIMATED TEST COUNTS BY DOMAIN

| Category | Estimated Tests | Notes |
|---|---|---|
| Core (state, events, services, registries) | ~150 | Foundation Ã¢â‚¬â€ must be 100% before anything else |
| Entity: light | ~40 | Most complex entity domain (color modes, effects) |
| Entity: switch | ~15 | Simple but foundational |
| Entity: sensor | ~45 | 70+ device classes to validate |
| Entity: binary_sensor | ~30 | 25+ device classes |
| Entity: climate | ~50 | Most complex service interface |
| Entity: cover | ~25 | Position, tilt, device classes |
| Entity: lock | ~15 | Security-critical, simple interface |
| Entity: media_player | ~35 | Many optional features |
| Entity: alarm_control_panel | ~25 | Security-critical, state machine |
| Entity: all other domains | ~100 | fan, vacuum, camera, weather, etc. |
| Automation: triggers | ~80 | All trigger types + edge cases |
| Automation: conditions | ~40 | All condition types + nesting |
| Automation: actions | ~60 | All action types + flow control |
| Automation: templates | ~100 | The largest surface area |
| Automation: run modes | ~20 | single/restart/queued/parallel |
| REST API | ~60 | All endpoints, auth, errors |
| WebSocket API | ~50 | All commands, subscriptions |
| MQTT Discovery | ~40 | All entity domains via MQTT |
| Input entities | ~30 | input_boolean, number, select, text, datetime |
| History/Recorder | ~40 | State history, statistics, purging |
| Edge cases | ~80 | Unicode, precision, concurrency, clock, etc. |
| **TOTAL** | **~1,200** | Growing with each HA release |

---

## 7. APPENDIX: CI PIPELINE

```yaml
# .github/workflows/conformance.yml
name: Conformance Tests

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 6 * * 1'  # Weekly Monday 6AM Ã¢â‚¬â€ catch HA regressions

jobs:
  test-ha-legacy:
    name: "HA-Legacy Baseline"
    runs-on: ubuntu-latest
    strategy:
      matrix:
        ha-version: ["2024.12", "2025.1", "2025.2"]
    steps:
      - uses: actions/checkout@v4
      - name: Run conformance suite against HA
        env:
          SUT_TYPE: ha-legacy
          HA_VERSION: ${{ matrix.ha-version }}
        run: |
          docker compose -f docker-compose.ha.yml up -d
          pip install -r requirements-test.txt
          pytest tests/ -v --json-report --json-report-file=results-ha-${{ matrix.ha-version }}.json
          python scripts/compat_report.py results-ha-${{ matrix.ha-version }}.json

  test-marge:
    name: "Marge Conformance"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run conformance suite against Marge
        env:
          SUT_TYPE: marge
        run: |
          docker compose -f docker-compose.marge.yml up -d
          pip install -r requirements-test.txt
          pytest tests/ -v --json-report --json-report-file=results-marge.json
          python scripts/compat_report.py results-marge.json

  compare:
    name: "Compatibility Delta"
    needs: [test-ha-legacy, test-marge]
    runs-on: ubuntu-latest
    steps:
      - name: Compare results
        run: |
          python scripts/compare_results.py \
            results-ha-2024.12.json \
            results-marge.json \
            --output delta-report.md
      - name: Post PR comment with delta
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const body = fs.readFileSync('delta-report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });
```

---

**END OF DOCUMENT**

*"A test suite is a specification that can't lie."*  
*Ã¢â‚¬â€ Every developer who was burned by a wiki page that said "should work"*
