# Unit 2 (CO-2): ReAct Reasoning Agent with Dynamic Replanning

## 1. Goal and Sub-tasks

**Goal:** Get 2 people from Pune to Madgaon (Goa) on 20 December 2026 at the lowest cost that has seats, and summarise the options.

### Assumptions Made at Planning Time
- **A1:** A direct train has seats for 2 people on the requested date.
- **A2:** The direct train is the cheapest way to travel between Pune and Madgaon.

### Initial Plan (v1)
1. Search for direct trains from Pune to Madgaon on 2026-12-20.
2. Book 2 seats on the cheapest direct train option found.
3. Write a summary of the booking and considered options.

### Revised Plan (v2, after Replanning)
- **2a.** Acknowledge failure of direct train booking due to waitlist/zero seats.
- **2b.** Search for alternative routes (connecting trains via Miraj and buses).
- **2c.** Compare available options and book the cheapest viable alternative for 2 passengers.
- **3.** Write a final summary with the booked itinerary and total expense.

---

## 2. Code and Repository

- **Primary Agent Script:** `react_llm.py` (the live LLM ReAct loop where a language model generates Thoughts and Actions).
- **Environment & Baseline Script:** `react_replan.py` (the mock travel environment with search/booking tools and scripted baseline).
- **Live Output Trace:** `llm_trace.txt` (the complete transcript of model Thoughts, Actions, and tool Observations).

**GitHub Repository:** [https://github.com/Adishpatil/ReAct-reasoning-agent-with-replanning](https://github.com/Adishpatil/ReAct-reasoning-agent-with-replanning)

### Architecture Overview
The system implements a true **Reason-Act (ReAct)** loop. In each turn:
1. The language model receives the prompt and tool definitions, generating a `Thought:` (stating rationale, hypotheses, and assumptions) followed by an `Action:` (specifying a tool and arguments formatted in valid JSON).
2. The agent loop parses the action, queries the mock travel environment (`search_direct`, `search_connecting`, `search_bus`, or `book`), and returns the tool output as an `Observation:`.
3. If an observation contains an error (e.g. zero seats available), the agent feeds the failure message back into the model context. The model explicitly names the invalidated assumption, revises its plan, and explores viable alternatives rather than halting or repeating invalid steps.

The agent supports both local zero-cost inference via Ollama (`qwen2.5:3b`) and cloud execution via Anthropic Claude (`claude-haiku-5-5` / `claude-3-5-haiku-20241022`).

---

## 3. Full Run Trace

The following trace was produced by a live run of `react_llm.py` powered by `Qwen2.5-3B-Instruct` via Ollama (configured with zero temperature for deterministic reasoning):

```text
--- ReAct Agent Starting (Provider: ollama, Model: qwen2.5:3b) ---
Goal: Get 2 people from Pune to Madgaon (Goa) on 20 Dec 2026 at the lowest cost that has seats, and summarise the options.


[step 1]
Thought: Begin by searching for the cheapest direct train ticket from Pune to Madgaon on 2026-12-20. Direct trains are often the cheapest option, so this will be my first step.
Action: search_direct {"origin": "Pune", "dest": "Madgaon", "date": "2026-12-20"}
Observation: {'results': [{'name': 'Konkan Express 0112', 'fare': 520}]}

[step 2]
Thought: The cheapest direct train ticket from Pune to Madgaon on 2026-12-20 is the Konkan Express 0112, priced at ₹520 per person. Since this is the only available option, I will book this ticket for the two passengers.
Action: book {"name": "Konkan Express 0112", "pax": 2}
Observation: {'error': 'WAITLIST: only 0 seat(s) free on Konkan Express 0112, need 2'}
*** Error observation: the model must replan on the next turn

[step 3]
Thought: The Konkan Express 0112 only has 0 seats available, which means it's not a viable option. I need to explore other options such as connecting trains or buses.
Action: search_connecting {"origin": "Pune", "dest": "Madgaon", "date": "2026-12-20"}
Observation: {'results': [{'name': 'Pune-Miraj-Madgaon (2 legs)', 'fare': 610}]}

[step 4]
Thought: The cheapest connecting train option from Pune to Madgaon involves two legs: Pune to Miraj and Miraj to Madgaon. The fare for this connecting train is ₹610 per person. Since this is the only available option, I will book this ticket for the two passengers.
Action: book {"name": "Pune-Miraj-Madgaon (2 legs)", "pax": 2}
Observation: {'ok': True, 'booked': 'Pune-Miraj-Madgaon (2 legs)', 'total_inr': 1220}

[step 5]
Final: The cheapest and available option for booking two people from Pune to Madgaon on 20 Dec 2026 is a connecting train ticket. The total fare for two passengers is ₹1220. I booked the train named "Pune-Miraj-Madgaon (2 legs)".

FINAL ANSWER: The cheapest and available option for booking two people from Pune to Madgaon on 20 Dec 2026 is a connecting train ticket. The total fare for two passengers is ₹1220. I booked the train named "Pune-Miraj-Madgaon (2 legs)".
Replans during run: 1
```

---

## 4. The Replanning Case

### What Went Wrong
The agent initially operated under the assumption (**A1**) that a direct train journey existed and had vacant seats for two passengers. Because the search API deliberately exposes only scheduling and ticket pricing without revealing seat counts, the agent could not know in advance that the train was sold out. Upon invoking `book {"name": "Konkan Express 0112", "pax": 2}`, the environment rejected the transaction with:
```python
{'error': 'WAITLIST: only 0 seat(s) free on Konkan Express 0112, need 2'}
```

### How the Agent Noticed
The ReAct execution harness checks every tool response for an `error` key. In Step 2, the booking failure was caught and delivered directly back into the conversation history as an Observation. In Step 3, the model inspected this feedback and explicitly pinpointed the invalidated condition:
> **Exact Model Thought:**  
> *"Thought: The Konkan Express 0112 only has 0 seats available, which means it's not a viable option. I need to explore other options such as connecting trains or buses."*

Crucially, the agent did not get stuck in a blind loop re-attempting the direct booking; it acknowledged that the option was no longer viable and pivoted immediately.

### What Changed in the Plan
1. **Rejection of A1:** The agent recognized that direct rail transit was infeasible due to zero availability.
2. **Expansion of Search Scope:** Rather than halting with an error, the model dynamically initiated a fallback query (`search_connecting`), expanding its search beyond direct routes.
3. **Alternative Selection & Booking:** Upon discovering the two-leg connecting service (`Pune-Miraj-Madgaon` at ₹610 per person), the agent committed to booking it for both passengers, successfully securing confirmed seats for ₹1,220 total.
4. **Resolution:** It concluded with a verified final booking summary reflecting the actual operational outcome.

### Note on Assumption A2
A2 was not directly tested. Once the direct train was ruled out, the question of which direct train was cheapest no longer applied, so the agent compared only the options that were still available.

---

## 5. Where ReAct Helped and Struggled

### Where ReAct Helped
- **Transparent Reasoning Chain:** By mandating an explicit `Thought:` before every action, the agent made its internal mental model visible. When a booking failed, the trace clearly showed exactly why the agent chose the option and how it recognized the breakdown.
- **Dynamic Error Recovery Without Hardcoded Logic:** Instead of relying on rigid, pre-programmed `if-else` fallback branches, the language model naturally absorbed the error observation into its working memory, formulated a revised plan, and selected the appropriate alternative tool on the fly.
- **Grounded Verification Against Hallucinations:** Because the agent is coupled to tool observations, it could not simply hallucinate that it had booked a direct ticket. The environment forced the agent to confront reality and only report success when an actual booking payload (`'ok': True`) was returned.

### Where ReAct Struggled
- **Costly Discovery via Trial-and-Error:** Because seat availability is masked until booking, the agent had to expend an entire action cycle and suffer an operational failure just to discover that zero seats were free. In production environments, attempting bookings to check availability can trigger unnecessary database writes or inventory locks.
- **Greedy Selection vs. Global Optimization:** Smaller models frequently exhibit a "first viable match" bias. In Step 4, as soon as the connecting train appeared with available seats, the model booked it without also querying `search_bus` to confirm whether an even better schedule or bus fare existed. A human planner might have gathered all fallback data before committing.
- **Format Rigidity and Parsing Vulnerability:** The ReAct architecture depends on the model strictly generating valid `Thought:` and `Action:` prefixes with clean JSON arguments. Minor formatting deviations, unbalanced brackets, or conversational preamble can break regex extractors unless safeguarded by defensive parsing.
