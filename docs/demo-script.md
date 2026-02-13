# Demo Script — 15-Minute Highlight Reel

**Setup:** Dashboard at `http://localhost:3000`, full screen, dark room.
**Speed:** 10x real time (configurable via `SPEED=` env var).
**Keyboard:** `S` = score card, `?` = help, `Escape` = dismiss overlays.

---

## Pre-Demo Checklist

```bash
# Start the full Docker stack
./scripts/run-demo.sh docker

# Verify: open http://localhost:3000
# Both status badges should show "online", house renders
# HA events counter should be incrementing (proves WebSocket auth works)
```

---

## Run the Highlight Reel

```bash
./scripts/run-demo.sh docker-highlight
```

This runs 5 chapters sequentially: dawn → morning → sunset → goodnight → outage.
The annotation banner at the top of the dashboard narrates what's happening.
Verification scores update live in the sidebar.

---

## Chapter 1: DAWN (3 min at 10x)

**What happens on screen:**
- Bedroom light turns on at 20% warm white
- Thermostat shifts to heat mode (Marge) / stays off (HA)
- Coffee maker switches on
- Annotation banner: "Morning automation should fire"

**What to say:**
> "This is a simulated 24-hour day in a house. Same events, same automations,
> same outcomes — running against Home Assistant and Marge simultaneously.
> They share the same visualization because the states should be identical."

> "The morning automation just fired. Three service calls, four state changes.
> Both platforms handled it. But look at the memory: HA is at 160 MB.
> Marge is at 8 MB. For the same job."

---

## Chapter 2: MORNING (1 min at 10x)

**What happens on screen:**
- Front door opens and closes (someone leaves for work)
- Entryway motion triggers — but security automation does NOT fire
  (alarm is armed_home, not armed_away)
- Verify sidebar shows HA dropped a point (alarm unavailable)

**What to say:**
> "Front door event. The security automation evaluated its condition —
> alarm is armed_home, not armed_away — so it correctly did nothing.
> That's a conditional automation. Both platforms got it right."

---

## Skip: DAYTIME + EVENING

> "I'm going to skip ahead past the daytime — 11 hours of sensor noise,
> about 2000 state changes. Nothing dramatic. Let's jump to sunset."

---

## Chapter 3: SUNSET (1.5 min at 10x)

**What happens on screen:**
- Porch and pathway lights turn on
- Evening scene fires: 4 living room lights + media player
- Accent light shows amber RGB color

**What to say:**
> "Sunset event. Exterior lights on. Evening scene applied — that's
> four lights and a media player in a single batch. Notice the accent
> light is showing the actual RGB color from the scene definition."

---

## Chapter 4: GOODNIGHT (1 min at 10x)

**What happens on screen:**
- All 9 lights turn off
- Both doors lock
- Thermostat adjusts
- Alarm arms for night
- Media player turns off
- Coffee maker turns off

**What to say:**
> "Bedside button pressed. The goodnight routine: 9 lights off, 2 locks,
> thermostat to night mode, alarm armed, media off. That's 14 state changes
> from one button press."

> "Check the verify scores in the sidebar. Marge is at 21/21.
> HA is at 17/21 — it struggles with some MQTT entity types."

> "Now here's where it gets interesting."

---

## Chapter 5: OUTAGE (3 min at 10x) — THE MONEY SHOT

**What happens on screen:**
- Power outage overlay appears with warning icon
- Both systems go offline (Docker containers stopped)
- Recovery race: live timers count up
- Marge recovers in ~3 seconds
- HA recovers in ~6-20 seconds
- Score card auto-shows after scenario completes

**What to say:**

*[When overlay appears]*
> "Power cut. Both platforms are down. This is the same failure mode
> your production systems face — unplanned restart."

*[When Marge recovers]*
> "Marge is back. [pause] That was under 3 seconds. Static binary,
> no interpreter, no package loading."

*[While waiting for HA]*
> "We're still waiting for Home Assistant. It's loading Python,
> importing packages, parsing YAML, starting integrations..."

*[When HA recovers]*
> "There it is. [read the times] Same house, same automations.
> Different foundations."

---

## Score Card

Auto-shows after outage, or press `S` manually.

**What to say:**
> "Let me put the numbers side by side."

*[Point at each row]*
> "Memory: 160 meg vs 8 meg — 20x smaller. Latency: 23 milliseconds vs
> 9 microseconds — three orders of magnitude. Startup: 94 seconds vs
> half a millisecond. Recovery time: you just saw it."

> "Verifications: Marge handled 21 out of 21 correctly. HA missed 4 due to
> MQTT integration quirks. Same events. Same automations."

> "This is a personal side project. One person. Four days. With AI."

*[Pause]*

> "The hard part wasn't writing code. The hard part was writing a spec
> rigorous enough that an AI could iterate against it. The CTS is 77 tests.
> The spec is MIL-STD-498 format. THAT's where the engineering went.
> The Rust came from an LLM that could verify its own work."

*[Final beat]*

> "Now imagine applying this to what we ship."

---

## If Things Go Wrong

- **HA won't start:** Demo still works with just Marge. Skip the comparison framing, focus on the architecture and the metrics.
- **Outage overlay doesn't trigger:** Press Escape, explain the numbers verbally, show the score card.
- **WebSocket disconnects:** Dashboard auto-reconnects in 3 seconds.
- **Scenario driver crashes:** Restart the chapter. State persists in both platforms.
- **HA token expired:** Run `bash scripts/ha-refresh-token.sh` (docker-highlight does this automatically).
- **Someone asks about production readiness:** "This is a demo subset — 12 entity domains out of 30+, 6 automations, no auth, no persistence. The architecture scales. The demo proves the foundations."
