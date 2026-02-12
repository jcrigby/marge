# Demo Script — 15-Minute Highlight Reel

**Setup:** Dashboard at `http://localhost:3000`, full screen, dark room.
**Speed:** 10x real time. Use `--chapter` to skip between chapters.
**Keyboard:** `S` = score card, `Escape` = dismiss overlays.

---

## Pre-Demo Checklist

```bash
./scripts/run-demo.sh start          # Starts mosquitto, HA, Marge
open http://localhost:3000            # Dashboard
# Verify: both status badges show "online", house renders
```

---

## Chapter 1: DAWN (3 min at 10x)

```bash
./scripts/run-demo.sh scenario dawn
```

**What happens on screen:**
- Bedroom light turns on at 20% warm white
- Thermostat shifts from 66 to 70
- Coffee maker switches on

**What to say:**
> "This is a simulated 24-hour day in a house. Same events, same automations,
> same outcomes — running against Home Assistant on the left... sorry, on the
> top... and Marge on the bottom. Actually they share the same visualization
> because the states are identical. Watch the sidebar metrics."

> "The morning automation just fired. Three service calls, four state changes.
> Both platforms handled it. But look at the memory: HA is at 780 MB.
> Marge is at 9 MB. For the same job."

---

## Chapter 2: MORNING (1 min at 10x)

```bash
./scripts/run-demo.sh scenario morning
```

**What happens on screen:**
- Front door opens and closes (someone leaves for work)
- Entryway motion triggers — but security automation does NOT fire
  (alarm is armed_home, not armed_away)

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

```bash
./scripts/run-demo.sh scenario sunset
```

**What happens on screen:**
- Porch and pathway lights turn on
- Evening scene fires: 4 living room lights + media player
- Accent light shows amber RGB color

**What to say:**
> "Sunset event. Exterior lights on. Evening scene applied — that's
> four lights and a media player in a single batch. Notice the accent
> light is showing the actual RGB color from the scene definition.
> Both platforms processed the same scene. Same result."

---

## Skip to GOODNIGHT

> "Let's skip to bedtime."

---

## Chapter 4: GOODNIGHT (1 min at 10x)

```bash
./scripts/run-demo.sh scenario goodnight
```

**What happens on screen:**
- All 9 lights turn off
- Both doors lock
- Thermostat drops to 66
- Alarm arms for night
- Media player turns off
- Coffee maker turns off

**What to say:**
> "Bedside button pressed. The goodnight routine: 9 lights off, 2 locks,
> thermostat to night mode, alarm armed, media off. That's 14 state changes
> from one button press. Both platforms handled all of them."

> "Now here's where it gets interesting."

---

## Chapter 5: OUTAGE (3 min at 10x) — THE MONEY SHOT

```bash
./scripts/run-demo.sh scenario outage
```

**What happens on screen:**
- Power outage overlay appears
- Both systems go offline
- Recovery race: live timers count up
- Marge recovers in ~1-2 seconds
- HA recovers in ~90+ seconds
- Overlay auto-dismisses after both recover

**What to say:**

*[When overlay appears]*
> "Power cut. Both platforms are down. This is the same failure mode
> your production systems face — unplanned restart."

*[When Marge recovers]*
> "Marge is back. [pause] That was under 2 seconds."

*[While waiting for HA]*
> "We're still waiting for Home Assistant. It's loading Python,
> importing 3800 packages, parsing YAML, starting integrations..."

*[When HA recovers]*
> "There it is. [read the times] Marge recovered in X seconds.
> HA took Y seconds. Same house, same automations, same outcomes.
> Different foundations."

---

## Score Card

Press `S` to show the score card.

**What to say:**
> "Let me put the numbers side by side."

*[Point at each row]*
> "Memory: 780 meg vs 9 meg. Latency: 23 milliseconds vs 5 microseconds.
> Startup: 94 seconds vs half a millisecond. Recovery time: you just saw it.
> Same events. Same automations. Same outcomes."

> "This is a personal side project. One person. Four days. With AI."

*[Pause]*

> "The hard part wasn't writing code. The hard part was writing a spec
> rigorous enough that an AI could iterate against it. The CTS is 74 tests.
> The spec is MIL-STD-498 format. THAT's where the engineering went."

*[Final beat]*

> "Now imagine applying this to what we ship."

---

## If Things Go Wrong

- **HA won't start:** Demo still works with just Marge. Skip the comparison framing, focus on the architecture and the metrics.
- **Outage overlay doesn't trigger:** Press Escape, explain the numbers verbally, show the score card.
- **WebSocket disconnects:** Dashboard auto-reconnects. Wait 3 seconds.
- **Scenario driver crashes:** Restart the chapter. State persists in both platforms.
- **Someone asks about production readiness:** "This is a demo subset — 12 entity domains out of 30+, 6 automations, no auth, no persistence. The architecture scales. The demo proves the foundations."
