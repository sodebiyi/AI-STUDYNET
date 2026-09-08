"""
NetMentor AI Coach — Socratic troubleshooting engine.

Per the product principle "Do not give the answer immediately", this
engine never states the root cause unless the student explicitly asks for
a hint (and even then, hints escalate gradually) or has exhausted a
configurable number of failed diagnosis attempts.

Implementation note (see AI_COACH_PROVIDER in app/core/config.py): this is
a deterministic, rule-based dialogue engine — no external LLM call, no API
key required. It reasons over *observable investigation state* (which show
commands the student has actually run, in which order, categorised by OSI
layer) rather than free-text understanding, which keeps it honest: a
student can't talk their way to the answer without doing the work. The
public surface — `coach_reply()` and `generate_hint()` — is the seam a
future build would use to swap in a real LLM (e.g. call an LLM with this
same investigation-state context instead of the rule table below) without
changing any caller in app/api/coach.py.
"""
from __future__ import annotations

MAX_HINTS_BEFORE_STRONG_NUDGE = 2
FAILED_ATTEMPTS_BEFORE_HINT_OFFER = 3

L1_COMMANDS = {"show ip interface brief", "show interfaces", "show interfaces trunk"}
L2_COMMANDS = {"show vlan brief", "show mac address-table", "show spanning-tree", "show etherchannel summary"}
L3_COMMANDS = {"show ip route", "show ip ospf neighbor", "show ip bgp", "show arp", "ping", "traceroute"}
CONFIG_VERBS = ("shutdown", "no shutdown", "switchport access vlan", "ip address", "ip route", "ip ospf area")


def _categorize(commands: list[dict]) -> dict[str, int]:
    counts = {"l1": 0, "l2": 0, "l3": 0, "config": 0, "other": 0}
    for c in commands:
        cmd = c["command"].strip().lower()
        if any(cmd.startswith(v) for v in CONFIG_VERBS):
            counts["config"] += 1
        elif cmd in L1_COMMANDS or cmd.startswith("show interfaces"):
            counts["l1"] += 1
        elif cmd in L2_COMMANDS:
            counts["l2"] += 1
        elif cmd in L3_COMMANDS or cmd.startswith("ping") or cmd.startswith("traceroute"):
            counts["l3"] += 1
        else:
            counts["other"] += 1
    return counts


def _mentions_any(message: str, words: tuple[str, ...]) -> bool:
    m = message.lower()
    return any(w in m for w in words)


def opening_message(incident_title: str) -> str:
    return (
        f"Hi, I'm NetMentor — I'll coach you through this one rather than solve it for you.\n\n"
        f"We've got a ticket: \"{incident_title}\". Before you touch any configuration, "
        f"let's gather evidence. What have you verified so far?"
    )


def coach_reply(
    incident_def: dict,
    commands: list[dict],
    failed_attempts: int,
    hints_used: int,
    student_message: str,
) -> str:
    msg = student_message.strip()
    counts = _categorize(commands)
    total_show_commands = counts["l1"] + counts["l2"] + counts["l3"]

    # Direct requests for the answer are redirected unless the student has
    # clearly struggled — handled separately via the dedicated /hint
    # endpoint, but we also catch it in free chat so the coach stays in
    # character.
    if _mentions_any(msg, ("what's the answer", "what is the answer", "just tell me", "give me the answer", "what's wrong", "what is wrong")):
        if failed_attempts >= FAILED_ATTEMPTS_BEFORE_HINT_OFFER:
            return (
                "I can see you've made a few attempts already — that's fine, this is how troubleshooting "
                "works. Rather than hand you the root cause, use the 'Request Hint' button when you're ready; "
                "it'll give you a graduated nudge instead of the full answer. In the meantime: of the layers "
                "you've checked, which one still hasn't been ruled out?"
            )
        return (
            "I won't just give you the root cause — that's not how you build the instinct for this. "
            "Let's keep working the problem systematically. What have you verified so far, and what does "
            "the evidence tell you?"
        )

    if total_show_commands == 0 and counts["config"] == 0:
        return (
            "Let's start with the fundamentals: what would you check first to scope this problem? "
            "In a real NOC you'd confirm the symptom, then work up from Layer 1. Try running a `show` "
            "command in the CLI below to gather some evidence."
        )

    if counts["l1"] == 0:
        return (
            "Good start. Before assuming this is a configuration problem higher up the stack, have you "
            "ruled out Layer 1? Check interface and line-protocol status first."
        )

    if counts["l1"] > 0 and counts["l2"] == 0 and incident_def["category"] in ("VLAN", "Layer 1"):
        return (
            "Interfaces are worth confirming, but connectivity problems on a switched network often live "
            "at Layer 2. What would you check next to rule out a VLAN or trunking issue?"
        )

    if counts["l2"] > 0 and counts["l3"] == 0 and "Routing" in incident_def["category"] or (counts["l1"] > 0 and counts["l3"] == 0 and "Routing" in incident_def["category"]):
        return (
            "Layer 1 and Layer 2 are worth confirming quickly, but this smells like a routing problem "
            "given the symptoms. What would the routing table tell you here?"
        )

    if counts["config"] > 0 and not _mentions_any(msg, ("verify", "checked", "confirm", "tested")):
        return (
            "You've made a configuration change — good. Before you consider this closed, how are you going "
            "to verify the fix actually resolved the symptom the ticket described?"
        )

    if _mentions_any(msg, ("i think", "root cause", "the problem is", "because", "it's")):
        return (
            "That's a reasonable hypothesis. What evidence from the commands you've already run supports "
            "it — and what would you check to confirm before making a change?"
        )

    if total_show_commands >= 2:
        return (
            "You're building a good evidence trail. Walk me through what you've ruled out and what's left "
            "on your list — that'll tell us both what to check next."
        )

    return (
        "Keep going systematically — what does the evidence you've gathered so far point to, and what's "
        "the next thing you'd check to confirm or rule it out?"
    )


def generate_hint(incident_def: dict, hint_level: int) -> str:
    """hint_level: 1 (nudge) -> 2 (stronger) -> 3 (near-answer)."""
    answer = incident_def["answer_key"]
    category = incident_def["category"]

    if hint_level <= 1:
        layer_hint = {
            "VLAN": "Focus on Layer 2 — specifically, what VLAN is assigned to the affected port versus what it should be.",
            "Layer 1": "Focus on Layer 1 — check whether every interface along the path is both administratively and operationally up.",
            "Layer 3 - IP Addressing": "Focus on the end host's own IP configuration — specifically the subnet mask, not just the address.",
            "Layer 3 - Routing": "Focus on the router closest to the source — does its routing table actually have an entry that covers the destination?",
            "Routing - OSPF": "Focus on the OSPF adjacency between the two routers before assuming the route itself is missing — no adjacency means no learned routes.",
        }.get(category, "Re-check each OSI layer in order — don't skip straight to a guess.")
        return f"Hint (1/3): {layer_hint}"

    if hint_level == 2:
        return f"Hint (2/3): Take a close look at {', '.join(answer['key_commands'][:2])} — the discrepancy will be visible in that output."

    return f"Hint (3/3, near-answer): {answer['root_cause']}"
