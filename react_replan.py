#!/usr/bin/env python3
"""
react_replan.py
A minimal ReAct agent (Thought -> Action -> Observation) that breaks a goal into
sub-tasks, executes them against a mock environment, and replans when a step fails.

The Thought step is rule-based so the run is reproducible with no API key.
To use an LLM, replace the scripted 'thought' strings with a model call that
returns (thought, action); the loop, tools and replanning logic stay the same.
"""

DATE, ORIGIN, DEST, PAX = "2026-12-20", "Pune", "Madgaon", 2
GOAL = ("Get 2 people from Pune to Madgaon (Goa) on 20 Dec 2026 at the lowest "
        "cost that has seats, and summarise the options.")

# ---- mock environment -------------------------------------------------------
# Search tools reveal fares but NOT seat counts; seats are only checked at booking.
SEATS = {"Konkan Express 0112": 0,                 # actually full
         "Pune-Miraj-Madgaon (2 legs)": 20,
         "Neeta Tours overnight bus": 30}
FARE = {"Konkan Express 0112": 520,
        "Pune-Miraj-Madgaon (2 legs)": 610,
        "Neeta Tours overnight bus": 900}

def search_direct(origin, dest, date):
    if (origin, dest, date) != (ORIGIN, DEST, DATE):
        return {"error": "no timetable for this route/date"}
    return {"results": [{"name": "Konkan Express 0112", "fare": FARE["Konkan Express 0112"]}]}

def search_connecting(origin, dest, date):
    return {"results": [{"name": "Pune-Miraj-Madgaon (2 legs)", "fare": FARE["Pune-Miraj-Madgaon (2 legs)"]}]}

def search_bus(origin, dest, date):
    return {"results": [{"name": "Neeta Tours overnight bus", "fare": FARE["Neeta Tours overnight bus"]}]}

def book(name, pax):
    if name not in SEATS:
        return {"error": f"unknown option: {name}"}
    if SEATS[name] < pax:
        return {"error": f"WAITLIST: only {SEATS[name]} seat(s) free on {name}, need {pax}"}
    SEATS[name] -= pax
    return {"ok": True, "booked": name, "total_inr": FARE[name] * pax}

TOOLS = {"search_direct": search_direct, "search_connecting": search_connecting,
         "search_bus": search_bus, "book": book}

# ---- helpers ----------------------------------------------------------------
def task(id_, desc, thought, tool, args, store=None):
    return {"id": id_, "desc": desc, "thought": thought, "tool": tool,
            "args": args, "store": store}

def cheapest(m):
    options = m["connecting"] + m["bus"]
    return min(options, key=lambda o: o["fare"])["name"]

# ---- agent ------------------------------------------------------------------
class Agent:
    def __init__(self):
        self.memory = {}
        self.assumptions = {
            "A1": "A direct train has seats for 2 people on the date.",
            "A2": "The direct train is the cheapest way to go.",
        }
        self.plan = []

    def initial_plan(self):
        return [
            task("1", "List direct trains Pune -> Madgaon",
                 "I need the direct options first. I am assuming A1 (seats exist); booking will test it.",
                 "search_direct", lambda m: (ORIGIN, DEST, DATE), store="direct"),
            task("2", "Book 2 seats on the cheapest direct train",
                 "A2 says the direct train is cheapest, so I will book it for 2 passengers.",
                 "book", lambda m: (m["direct"][0]["name"], PAX), store="booking"),
            task("3", "Write summary", None, None, None),
        ]

    def replan(self, failed, obs):
        failed_name = failed["args"](self.memory)[0]
        self.memory["rejected"] = (failed_name, obs["error"])
        self.assumptions["A1"] += "  [REJECTED]"
        print("\n*** REPLAN TRIGGERED")
        print(f"    Step {failed['id']} failed: {obs['error']}")
        print("    Assumption A1 is false: the direct train has no seats.")
        print("    Revised plan:")
        self.plan = [
            task("2a", "Search connecting trains via Miraj",
                 "A1 is wrong, so the direct route is out. I need another route with seats.",
                 "search_connecting", lambda m: (ORIGIN, DEST, DATE), store="connecting"),
            task("2b", "Search buses as a fallback",
                 "Buses may still have seats. I will collect their fares to compare.",
                 "search_bus", lambda m: (ORIGIN, DEST, DATE), store="bus"),
            task("2c", "Book cheapest option for 2 passengers",
                 "I will book the lowest-fare option. If it has no seats, the booking fails and I replan again.",
                 "book", lambda m: (cheapest(m), PAX), store="booking"),
            task("3", "Write summary", None, None, None),
        ]
        for t in self.plan:
            print(f"      {t['id']}. {t['desc']}")

    def run(self, max_steps=10):
        print("GOAL:", GOAL)
        self.plan = self.initial_plan()
        print("\nINITIAL PLAN")
        for t in self.plan:
            print(f"  {t['id']}. {t['desc']}")
        print("ASSUMPTIONS")
        for k, v in self.assumptions.items():
            print(f"  {k}: {v}")
        print("\n--- TRACE ---")

        steps = 0
        while self.plan:
            steps += 1
            if steps > max_steps:
                raise RuntimeError("step budget exhausted")
            t = self.plan.pop(0)
            print(f"\n[step {t['id']}] {t['desc']}")
            if t["tool"] is None:
                print("Thought: Everything needed is gathered. Writing the summary.")
                self.summary()
                return
            args = t["args"](self.memory)
            print(f"Thought: {t['thought']}")
            print(f"Action: {t['tool']}{args}")
            obs = TOOLS[t["tool"]](*args)
            print(f"Observation: {obs}")
            if "error" in obs:
                self.replan(t, obs)
                continue
            if t["store"] == "booking":
                self.memory["booking"] = obs
            elif t["store"]:
                self.memory[t["store"]] = obs["results"]

    def summary(self):
        b = self.memory["booking"]
        print("\nFINAL ANSWER")
        print(f"Booked {b['booked']} for {PAX} passengers: INR {b['total_inr']} total.")
        print("Options considered:")
        name, err = self.memory["rejected"]
        print(f"  - {name} (direct): INR {FARE[name]}/person, rejected ({err}).")
        for o in self.memory["connecting"] + self.memory["bus"]:
            print(f"  - {o['name']}: INR {o['fare']}/person")
        print("Assumption status:")
        for k, v in self.assumptions.items():
            print(f"  {k}: {v}")

if __name__ == "__main__":
    Agent().run()
