# Unit 2 (CO-2): ReAct Reasoning Agent with Dynamic Replanning

**Student Name:** Adish Patil  
**Date:** 21 November 2026  
**Assignment:** Unit 2 (CO-2) Practical Implementation — Reasoning & Action Agents  

---

## 1. Goal and Sub-tasks

**Goal:** Get 2 people from Pune to Madgaon (Goa) on 20 December 2026 at the lowest cost that has seats, and summarise the options.

### Assumptions Made at Planning Time
- **A1:** A direct train has seats for 2 people on the requested date.
- **A2:** The direct train is the cheapest way to travel.

### Initial Plan (v1)
1. List direct trains Pune -> Madgaon.
2. Book 2 seats on the cheapest direct train.
3. Write summary.

### Revised Plan (v2, after Replanning)
- **2a.** Search connecting trains via Miraj.
- **2b.** Search buses as a fallback.
- **2c.** Book the cheapest option with available seats for 2 passengers.
- **3.** Write summary.

---

## 2. Code

The code for this assignment consists of two scripts and the execution trace:
- **`react_llm.py`:** The main ReAct agent implementation where a language model autonomously generates `Thought:` and `Action:` turns in response to environment observations. It includes error parsing to trigger dynamic replanning.
- **`react_replan.py`:** The mock travel environment implementing search and booking tools (`search_direct`, `search_connecting`, `search_bus`, `book`), alongside a deterministic baseline agent.
- **`llm_trace.txt`:** The raw terminal output recording the complete live ReAct interaction.

**GitHub Repository:** [https://github.com/Adishpatil/ReAct-reasoning-agent-with-replanning](https://github.com/Adishpatil/ReAct-reasoning-agent-with-replanning)

The agent runs a continuous loop of Thought, Action, and Observation. In each turn, the model evaluates its current knowledge, generates an internal reasoning step, and selects an environment tool with JSON arguments. When an action returns an error (such as a booking failure caused by lack of seats), the harness injects the error back into the prompt history as an observation. The model identifies the invalid assumption, revises its strategy, and executes alternative tools until the goal is satisfied.

---

## 3. Full Run Trace

The trace below was captured from a live run of `react_llm.py` using `Qwen2.5-3B-Instruct` (via Ollama at temperature 0):

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
In my initial plan, the agent operated on the assumption (**A1**) that a direct train service would have open seats for 2 passengers. Because the environment's search tools only reveal timetables and ticket fares while keeping seat counts hidden until booking, the agent had no way of knowing beforehand whether the train was full. Consequently, when the agent called `book` on the Konkan Express 0112 in Step 2, the booking was rejected with:  
`{'error': 'WAITLIST: only 0 seat(s) free on Konkan Express 0112, need 2'}`.

### How the Agent Noticed
The execution loop inspects each tool output for an `error` key and supplies the returned dictionary directly to the model as an `Observation:`. In Step 3, the model read this observation, recognized that its attempt had failed, and explicitly reflected on the root cause in its Thought:

> **Exact Thought:**  
> *"Thought: The Konkan Express 0112 only has 0 seats available, which means it's not a viable option. I need to explore other options such as connecting trains or buses."*

Instead of blindly repeating the same action, the model immediately identified that the direct route was not viable and shifted its objective toward backup options.

### What Changed in the Plan
The agent abandoned assumption A1 regarding direct trains. It amended its plan to search for alternative transit modes, issuing `search_connecting` in Step 3. Upon finding the 2-leg route via Miraj at ₹610 per passenger, it proceeded in Step 4 to book those seats. The booking succeeded (`'ok': True`), and the agent wrapped up in Step 5 by presenting the confirmed itinerary and total cost (₹1,220).

### Note on A2
A2 was not directly tested. Once the direct train was ruled out, the question of which direct train was cheapest no longer applied, so the agent compared only the options that were still available.

---

## 5. Where ReAct Helped and Struggled

### Where ReAct Helped
- **Explicit Reasoning Trace:** The explicit `Thought:` step forced the agent to justify its actions beforehand. When the booking failed, the audit trail clearly documented that the failure stemmed from assumption A1 rather than a logic flaw in tool execution.
- **Dynamic Recovery without Hardcoded Logic:** Unlike a static script with hardcoded branching, the LLM naturally understood the natural-language error observation and synthesized a valid fallback strategy on its own.
- **Verification through Environmental Grounding:** By requiring tool confirmation before finalizing, the agent was prevented from hallucinating a successful booking. It had to wait for a confirmed `ok: True` payload before generating its final answer.

### Where ReAct Struggled
- **Costly Discovery through Trial-and-Error:** Because seat availability was unobservable during the initial search, the agent was forced to spend a booking attempt and trigger an error just to discover that seats were unavailable. In a live system, this wastes API calls and server transactions.
- **Greedy Option Selection:** In Step 4, as soon as the model found a connecting train with seats, it booked it immediately without running `search_bus` to check whether bus fares might be cheaper. It prioritized the first working alternative over an exhaustive search.
- **Fragility of Structured Generation:** The ReAct loop depends on strict syntax matching (`Thought:`, `Action:`, and valid JSON). If an LLM outputs unstructured conversational filler or malformed JSON, the parser fails unless robust fallbacks are in place.
