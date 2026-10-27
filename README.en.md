# WakeGate · 苏醒之门

**Wake a stopped AI agent — but only when it *should* wake.**

> Not a scheduled message. A scheduled message decides *what to say* at schedule time and fires it no matter what.
> WakeGate only **wakes the agent**; the agent decides whether to speak — and may decide to stay silent.

When an AI agent's turn ends, it stops. It will not remember to come back to you. Most "proactive companion" setups solve this with cron pushing a line into the chat: fixed time, fixed words, like a check-in robot.
This repo is the other approach: **judgement runs locally, waking costs money, and the woken agent decides what to do — including nothing.**

---

## 1. Where this sits on the proactivity spectrum

| Level | What it is | Examples |
|---|---|---|
| L0 | Answers only when asked | plain chatbot |
| L1 | Event-triggered | webhooks, GitHub bots |
| L2 | **Scheduled self-wake** | cron, daily digests |
| L3 | **Condition-monitored** | price alerts, monitors |
| L4 | Decides when to act on its own | always-on agents |

**WakeGate ≈ L3 (condition-triggered) + a bit of L4 (the woken agent self-decides).** The L2 timer is only the *entrance*; the decision happens after waking.

## 2. Three layers (all three required)

```
┌──────────────┐   every N min   ┌──────────────┐   only if "should wake"   ┌──────────────┐
│  Trigger      │ ──────────────▶ │  Judge        │ ────────────────────────▶ │  Wake channel │
│ cron / sched  │                 │ plain script  │                           │ resumes the   │
│               │                 │ (no tokens)   │                           │ stopped agent │
└──────────────┘                 └──────┬───────┘                           └──────┬───────┘
                                        │ writes a few-line state.json                 │
                                        ▼                                             ▼
                                 ┌──────────────┐                            ┌──────────────┐
                                 │ woken agent  │◀───────────────────────────│  the agent   │
                                 │ reads state  │                             │ decides      │
                                 └──────────────┘                            └──────────────┘
```

| Layer | Job | What you need |
|---|---|---|
| **1. Judge** | gather state → decide → write `should_wake` | a script that can read local state |
| **2. Wake channel** | **resume an already-stopped session** | a local HTTP door / plugin / CLI hook |
| **3. Trigger** | run the judge every N minutes | cron / systemd timer / Task Scheduler |

> **Without layer 2 this collapses into a logger.** No matter how good the judgement, you cannot wake a process that has stopped.

## 3. What it can do (scenarios)

| # | Situation | Reaction | Knobs |
|---|---|---|---|
| 1 | User has been quiet for a while | wake the agent → **it decides** to speak / act / **stay silent** | `silence_minutes`, `may_stay_silent` |
| 2 | User just spoke | do not disturb (with a desktop pet: not even a touch wakes the agent) | `silence_minutes`, `active_window_minutes` |
| 3 | Night / quiet hours | nothing fires (unless an exception) | `quiet_hours` |
| 4 | User is asleep (flag file) | nothing fires; after long sleep, check more often | `sleep_flag_path`, `wake_bonus_after_hours` |
| 5 | User is away from the keyboard *(needs an "is present" source)* | assume absent → do not wake | `active_window_minutes` |
| 6 | Argument / crisis | **all limits lifted** | `exception_argue` |
| 7 | User said "I'll be back, find me then" | wake on time | `exception_promise` |
| 8 | The desktop pet got poked angry *(optional integration)* | forced wake, skips thresholds | `exception_angry` |
| 9 | Unread message / calendar soon | wake immediately instead of waiting for the timer | `event_triggers` |
| 10 | "What's the situation right now?" | a few-line state snapshot for the agent, **no chat log dump** | `state_fields` |
| 11 | Reminder only, no agent autonomy | `action=notify` | `action` |
| 12 | Observe only, never disturb | `action=log` | `action`, `dry_run` |
| 13 | Same reason keeps firing | cooldown + hourly/daily caps + backoff when ignored | `cooldown_minutes`, `max_per_hour` |
| 14 | Wake channel temporarily unavailable | retry; **always leave a trace**, never fail silently | `retry` |
| 15 | Fixed good-morning message | doable, but that is L2 — ordinary cron is enough | — |

> Rows 2, 5 and 8 assume extra integrations (a companion UI that records "touch/poke", a presence source). **Without them those rows degrade to "conversation time only".** The core is just *conversation time + wake channel*.

### What it cannot do

| Cannot | Why |
|---|---|
| Guarantee the wake lands | channel down / host restart / no live session — retry and log, that's it |
| Decide what the agent says | it only wakes; speaking is the agent's call (fix the text and you are back to scheduled messages) |
| Sync across machines | the judge is local; move it and rewire `idle_source` / `message_source` |
| Read minds | every criterion is *visible local state*; it does not guess feelings |

## 4. What you can change

About 30 knobs in six groups — full tables in the Chinese `README.md` §3. Summary:

| Group | Knobs |
|---|---|
| Trigger | `interval_minutes`, `only_when_idle`, `event_triggers` |
| Criteria | `silence_minutes`, `active_window_minutes`, `idle_source`, `message_source`, `sleep_flag_path`, `quiet_hours`, `wake_bonus_after_hours`, `weekday_override` |
| Action | `action` (wake/notify/log), `content_source` (ai/template), `may_stay_silent`, `channel` |
| Rate limits | `cooldown_minutes`, `max_per_hour`, `max_per_day`, `backoff_on_ignored`, `retry`, `dry_run` |
| Exceptions | `exception_argue`, `exception_angry`, `exception_promise`, `exception_force_by_human` |
| Output | `state_path`, `state_fields`, `state_max_bytes` |

## 5. Cost: why this is cheap

1. **The judge is a plain script** — no model call. 144 runs a day cost nothing.
2. **State is a few-line JSON** (how long since last message, present/absent, asleep, arguing, should-wake). **You do not dump the chat log into the model.**
3. **No wake, no tokens.** A cron message fires and burns tokens whether or not it makes sense; this computes locally and only wakes when needed.
4. **No cloud, no subscription** — scheduler, local door and judge all live on your machine.

## 6. Four guardrails (without them it is not autonomy, it is runaway)

| Guardrail | Prevents |
|---|---|
| Thresholds | disturbing someone who just spoke |
| Cooldown / rate caps | the same event being reported forever (spam, cost) |
| Quiet hours + sleep flag | waking a sleeping human |
| Exception channel | real emergencies — **exceptions must override every limit** |

## 7. Three prerequisites

1. A **wake channel** that can resume a stopped session.
2. A **system-level scheduler** that survives session shutdown.
3. **Wrong wakes cost money**: each wake starts an inference turn. Worst case is an agent talking to itself all night.
   → **Suggested: three days of "observed trial"** — let it wake normally, but log one line of reasoning per wake so a human can tune thresholds.
   **Do not ship a "log only" dry run as the default** — users feel nothing and cannot see failures.

## 8. Quick start

```bash
cp criteria.example.json criteria.json   # then edit for your schedule
python judge.py                          # local judgement -> state.json
python knock.py                          # wake only if should_wake
# then schedule it every N minutes (cron / Task Scheduler)
```

`judge.py` and `knock.py` are **skeletons**: the decision logic is real, the *data sources* (`idle_source`, `message_source`) are yours to wire.

## 9. Who this is not for

- **"I want a fixed good-morning every day"** → that is L2, plain cron is enough.
- **No wake channel** → this becomes bookkeeping.
- **Will not tune thresholds** → untuned criteria means a disturb machine.

## 10. Status

Early. Extracted from a private implementation that ran on a Windows machine for two months, **with all personal schedules and names stripped**.
Issues with "your criteria table is missing X" are the most welcome kind.

MIT License. 中文说明见 [README.md](./README.md).
