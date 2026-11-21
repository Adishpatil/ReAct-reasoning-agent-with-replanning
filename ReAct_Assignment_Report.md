# Unit 2 (CO-2): ReAct Reasoning Agent with Dynamic Replanning

## 1. Goal and sub-tasks

**Goal:** Get 2 people from Pune to Madgaon (Goa) on 20 December 2026 at the lowest cost that has seats, and summarise the options.

**Assumptions made at planning time**
- A1: A direct train has seats for 2 people on the date.
- A2: The direct train is the cheapest way to go.

**Initial plan (v1)**
1. List direct trains Pune -> Madgaon
2. Book 2 seats on the cheapest direct train
3. Write summary

**Revised plan (v2, after replanning)**
- 2a. Search connecting trains via Miraj
- 2b. Search buses as a fallback
- 2c. Book the cheapest option for 2 passengers
- 3. Write summary

## 2. Code

`react_replan.py` (included in the submission folder; also paste or link your GitHub repo here).

The agent runs a loop of Thought, Action, and Observation. Each sub-task names a tool and its arguments. If an Observation contains an error, the agent calls `replan()`, which rejects the failed assumption and rebuilds the remaining plan. The Thought step is rule-based so the run is reproducible without an API key. To use a live model, replace the scripted thought strings with an LLM call that returns a Thought and an Action.

## 3. Full run trace

```
GOAL: Get 2 people from Pune to Madgaon (Goa) on 20 Dec 2026 at the lowest cost that has seats, and summarise the options.

INITIAL PLAN
  1. List direct trains Pune -> Madgaon
  2. Book 2 seats on the cheapest direct train
  3. Write summary
ASSUMPTIONS
  A1: A direct train has seats for 2 people on the date.
  A2: The direct train is the cheapest way to go.

--- TRACE ---

[step 1] List direct trains Pune -> Madgaon
Thought: I need the direct options first. I am assuming A1 (seats exist); booking will test it.
Action: search_direct('Pune', 'Madgaon', '2026-12-20')
Observation: {'results': [{'name': 'Konkan Express 0112', 'fare': 520}]}

[step 2] Book 2 seats on the cheapest direct train
Thought: A2 says the direct train is cheapest, so I will book it for 2 passengers.
Action: book('Konkan Express 0112', 2)
Observation: {'error': 'WAITLIST: only 0 seat(s) free on Konkan Express 0112, need 2'}

*** REPLAN TRIGGERED
    Step 2 failed: WAITLIST: only 0 seat(s) free on Konkan Express 0112, need 2
    Assumption A1 is false: the direct train has no seats.
    Revised plan:
      2a. Search connecting trains via Miraj
      2b. Search buses as a fallback
      2c. Book cheapest option for 2 passengers
      3. Write summary

[step 2a] Search connecting trains via Miraj
Thought: A1 is wrong, so the direct route is out. I need another route with seats.
Action: search_connecting('Pune', 'Madgaon', '2026-12-20')
Observation: {'results': [{'name': 'Pune-Miraj-Madgaon (2 legs)', 'fare': 610}]}

[step 2b] Search buses as a fallback
Thought: Buses may still have seats. I will collect their fares to compare.
Action: search_bus('Pune', 'Madgaon', '2026-12-20')
Observation: {'results': [{'name': 'Neeta Tours overnight bus', 'fare': 900}]}

[step 2c] Book cheapest option for 2 passengers
Thought: I will book the lowest-fare option. If it has no seats, the booking fails and I replan again.
Action: book('Pune-Miraj-Madgaon (2 legs)', 2)
Observation: {'ok': True, 'booked': 'Pune-Miraj-Madgaon (2 legs)', 'total_inr': 1220}

[step 3] Write summary
Thought: Everything needed is gathered. Writing the summary.

FINAL ANSWER
Booked Pune-Miraj-Madgaon (2 legs) for 2 passengers: INR 1220 total.
Options considered:
  - Konkan Express 0112 (direct): INR 520/person, rejected (WAITLIST: only 0 seat(s) free on Konkan Express 0112, need 2).
  - Pune-Miraj-Madgaon (2 legs): INR 610/person
  - Neeta Tours overnight bus: INR 900/person
Assumption status:
  A1: A direct train has seats for 2 people on the date.  [REJECTED]
  A2: The direct train is the cheapest way to go.
```

## 4. The replanning case

**What went wrong.** The plan assumed (A1) that the direct train had seats. The search tool only returned fares and timetables, not seat counts, so the agent could not know this during planning. The first booking attempt on the Konkan Express returned a waitlist error because zero seats were free.

**How the agent noticed.** The booking Observation contained an `error` key. The loop checks for this after every action, which triggered the replan. The agent did not continue with the plan as if the booking had succeeded.

**What it changed.** It marked A1 as rejected, dropped the step that depended on the direct train, and inserted three new sub-tasks: search connecting trains, search buses, and book the cheapest feasible option. It also kept the original summary step. The new plan booked the connecting train at INR 1,220 for two people, which is cheaper than the bus at INR 1,800.

**Note on A2.** A2 was also wrong in the sense that the direct train was not a viable option at all, so "cheapest" stopped being relevant. The agent handled this by comparing only the options that were still available, which is why the fallback search was needed.

## 5. Where ReAct helped and struggled

- **Helped:** The Thought-before-Action format made the planning assumptions visible, so the failure was easy to trace back to A1. The Observation check made recovery straightforward: the agent stopped, updated its beliefs, and continued.
- **Struggled:** The agent could only replan after an action failed, so it spent a booking attempt to discover information (seat counts) that a different search might have revealed. The rule-based thoughts also show the limit of a fixed plan: a real LLM would have to reason about unexpected observations, and it could also make up plausible-sounding but wrong facts.
- **Also:** Without a step budget and a clear stopping condition, a replanning loop could run indefinitely. The `max_steps` guard addresses this, but it would need tuning for longer goals.
