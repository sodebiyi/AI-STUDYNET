"""
The 5 MVP troubleshooting incidents (see product spec section 21 / 24).

Each incident bundles:
  - metadata (slug, title, difficulty, category, priority, summary, impact,
    symptoms, learning_objectives) -> safe to send to the client as-is
  - topology -> a nodes/edges description for the frontend diagram (no
    fault information leaks through this)
  - initial_state -> the full simulated device state INCLUDING the fault,
    consumed only by app/simulation/engine.py and app/simulation/cli.py
  - answer_key -> root cause / correct remediation / verification /
    scoring hints, NEVER serialized to the student-facing API

Extending the platform with new incidents means adding another entry to
INCIDENTS below (or, eventually, rows in the `incidents` table seeded by
the admin dashboard) — nothing in the engine, CLI, or API layer is
incident-specific.
"""
from __future__ import annotations


def _pc(ip, mask, gateway, mac):
    return {
        "kind": "pc",
        "interfaces": {"eth0": {"admin_status": "up", "status": "up", "ip": ip, "mask": mask, "gateway": gateway, "mac": mac}},
    }


def _server(ip, mask, gateway, mac):
    return {
        "kind": "server",
        "interfaces": {"eth0": {"admin_status": "up", "status": "up", "ip": ip, "mask": mask, "gateway": gateway, "mac": mac}},
    }


INCIDENTS: dict[str, dict] = {

    # ------------------------------------------------------------------
    "inc-001-vlan-mismatch": {
        "title": "PC Cannot Reach Gateway",
        "difficulty": "Beginner",
        "category": "VLAN",
        "priority": "P3",
        "summary": "A single user reports their PC cannot reach anything on the network, including the default gateway.",
        "impact": "One user (PC1) has no network connectivity. No other users are affected.",
        "symptoms": [
            "ping from PC1 to its default gateway (192.168.10.1) times out.",
            "PC1's IP configuration looks correct (192.168.10.20/24, gateway 192.168.10.1).",
        ],
        "learning_objectives": [
            "Understand access VLAN assignment on a switchport.",
            "Recognise that a correctly configured IP is useless if Layer 2 doesn't match.",
            "Practice reading 'show vlan brief' output.",
        ],
        "topology": {
            "nodes": [
                {"id": "PC1", "label": "PC1", "type": "pc"},
                {"id": "SW1", "label": "SW1", "type": "switch"},
                {"id": "R1", "label": "R1", "type": "router"},
            ],
            "edges": [
                {"from": "PC1", "to": "SW1", "from_if": "eth0", "to_if": "Fa0/5"},
                {"from": "SW1", "to": "R1", "from_if": "Gi0/1", "to_if": "Gi0/0"},
            ],
        },
        "initial_state": {
            "devices": {
                "PC1": _pc("192.168.10.20", "255.255.255.0", "192.168.10.1", "AAAA.BBBB.0001"),
                "SW1": {
                    "kind": "switch",
                    "vlans": {"10": "DATA", "20": "VOICE"},
                    "interfaces": {
                        "Fa0/5": {"admin_status": "up", "status": "up", "mode": "access", "access_vlan": 20},  # FAULT: should be 10
                        "Gi0/1": {"admin_status": "up", "status": "up", "mode": "access", "access_vlan": 10},
                    },
                },
                "R1": {
                    "kind": "router",
                    "interfaces": {
                        "Gi0/0": {"admin_status": "up", "status": "up", "ip": "192.168.10.1", "mask": "255.255.255.0", "mac": "CCCC.DDDD.0001"},
                    },
                    "static_routes": [],
                    "ospf": {"enabled": False},
                },
            },
            "links": [
                {"a_device": "PC1", "a_if": "eth0", "b_device": "SW1", "b_if": "Fa0/5"},
                {"a_device": "SW1", "a_if": "Gi0/1", "b_device": "R1", "b_if": "Gi0/0"},
            ],
        },
        "answer_key": {
            "root_cause": "SW1 interface Fa0/5 (PC1's access port) is assigned to VLAN 20 instead of VLAN 10, so PC1's frames never reach R1's VLAN 10 gateway interface.",
            "root_cause_keywords": ["vlan", "20", "10", "access", "fa0/5"],
            "correct_remediation": "On SW1, enter interface Fa0/5 and set 'switchport access vlan 10'.",
            "remediation_check": {"device": "SW1", "interface": "Fa0/5", "field": "access_vlan", "expected": 10},
            "verification": "ping 192.168.10.1 from PC1 succeeds (5/5).",
            "verify_check": {"device": "PC1", "dest_ip": "192.168.10.1"},
            "key_commands": ["show ip interface brief", "show vlan brief", "show running-config"],
        },
        "xp_reward": 100,
        "is_free_tier": True,
    },

    # ------------------------------------------------------------------
    "inc-002-interface-down": {
        "title": "Interface Administratively Down",
        "difficulty": "Beginner",
        "category": "Layer 1",
        "priority": "P3",
        "summary": "A user reports total loss of connectivity after their switch port was 'accidentally bumped' during maintenance.",
        "impact": "One user (PC1) has no network connectivity.",
        "symptoms": [
            "ping from PC1 to its default gateway (192.168.10.1) times out immediately.",
            "PC1's IP configuration is correct.",
        ],
        "learning_objectives": [
            "Understand administrative vs line-protocol interface status.",
            "Practice using 'show ip interface brief' to spot a shutdown port.",
        ],
        "topology": {
            "nodes": [
                {"id": "PC1", "label": "PC1", "type": "pc"},
                {"id": "SW1", "label": "SW1", "type": "switch"},
                {"id": "R1", "label": "R1", "type": "router"},
            ],
            "edges": [
                {"from": "PC1", "to": "SW1", "from_if": "eth0", "to_if": "Fa0/5"},
                {"from": "SW1", "to": "R1", "from_if": "Gi0/1", "to_if": "Gi0/0"},
            ],
        },
        "initial_state": {
            "devices": {
                "PC1": _pc("192.168.10.20", "255.255.255.0", "192.168.10.1", "AAAA.BBBB.0002"),
                "SW1": {
                    "kind": "switch",
                    "vlans": {"10": "DATA"},
                    "interfaces": {
                        "Fa0/5": {"admin_status": "down", "status": "down", "mode": "access", "access_vlan": 10},  # FAULT
                        "Gi0/1": {"admin_status": "up", "status": "up", "mode": "access", "access_vlan": 10},
                    },
                },
                "R1": {
                    "kind": "router",
                    "interfaces": {
                        "Gi0/0": {"admin_status": "up", "status": "up", "ip": "192.168.10.1", "mask": "255.255.255.0", "mac": "CCCC.DDDD.0002"},
                    },
                    "static_routes": [],
                    "ospf": {"enabled": False},
                },
            },
            "links": [
                {"a_device": "PC1", "a_if": "eth0", "b_device": "SW1", "b_if": "Fa0/5"},
                {"a_device": "SW1", "a_if": "Gi0/1", "b_device": "R1", "b_if": "Gi0/0"},
            ],
        },
        "answer_key": {
            "root_cause": "SW1 interface Fa0/5 is administratively down (shutdown), so PC1's link never comes up.",
            "root_cause_keywords": ["shutdown", "administratively down", "fa0/5"],
            "correct_remediation": "On SW1, enter interface Fa0/5 and issue 'no shutdown'.",
            "remediation_check": {"device": "SW1", "interface": "Fa0/5", "field": "admin_status", "expected": "up"},
            "verification": "ping 192.168.10.1 from PC1 succeeds (5/5).",
            "verify_check": {"device": "PC1", "dest_ip": "192.168.10.1"},
            "key_commands": ["show ip interface brief"],
        },
        "xp_reward": 80,
        "is_free_tier": True,
    },

    # ------------------------------------------------------------------
    "inc-003-wrong-ip": {
        "title": "Incorrect IP Address Configuration",
        "difficulty": "Beginner",
        "category": "Layer 3 - IP Addressing",
        "priority": "P3",
        "summary": "A newly imaged PC can't reach anything on the network after IT re-imaged it this morning.",
        "impact": "One user (PC1) has no network connectivity.",
        "symptoms": [
            "ping from PC1 to its default gateway (192.168.10.1) fails instantly with 'Destination host unreachable'.",
            "Layer 1 and Layer 2 (switchport, VLAN) all check out normally.",
        ],
        "learning_objectives": [
            "Understand subnet mask math and how it determines whether a gateway is 'local'.",
            "Practice methodically ruling out L1/L2 before suspecting L3.",
        ],
        "topology": {
            "nodes": [
                {"id": "PC1", "label": "PC1", "type": "pc"},
                {"id": "SW1", "label": "SW1", "type": "switch"},
                {"id": "R1", "label": "R1", "type": "router"},
            ],
            "edges": [
                {"from": "PC1", "to": "SW1", "from_if": "eth0", "to_if": "Fa0/5"},
                {"from": "SW1", "to": "R1", "from_if": "Gi0/1", "to_if": "Gi0/0"},
            ],
        },
        "initial_state": {
            "devices": {
                "PC1": _pc("192.168.10.20", "255.255.255.240", "192.168.10.1", "AAAA.BBBB.0003"),  # FAULT: /28 excludes .1
                "SW1": {
                    "kind": "switch",
                    "vlans": {"10": "DATA"},
                    "interfaces": {
                        "Fa0/5": {"admin_status": "up", "status": "up", "mode": "access", "access_vlan": 10},
                        "Gi0/1": {"admin_status": "up", "status": "up", "mode": "access", "access_vlan": 10},
                    },
                },
                "R1": {
                    "kind": "router",
                    "interfaces": {
                        "Gi0/0": {"admin_status": "up", "status": "up", "ip": "192.168.10.1", "mask": "255.255.255.0", "mac": "CCCC.DDDD.0003"},
                    },
                    "static_routes": [],
                    "ospf": {"enabled": False},
                },
            },
            "links": [
                {"a_device": "PC1", "a_if": "eth0", "b_device": "SW1", "b_if": "Fa0/5"},
                {"a_device": "SW1", "a_if": "Gi0/1", "b_device": "R1", "b_if": "Gi0/0"},
            ],
        },
        "answer_key": {
            "root_cause": "PC1 is configured with subnet mask 255.255.255.240 (/28), which puts it in a different logical subnet than its own default gateway (192.168.10.1), so the PC never even tries to reach it over the LAN.",
            "root_cause_keywords": ["subnet mask", "255.255.255.240", "/28", "gateway", "unreachable"],
            "correct_remediation": "On PC1, correct the subnet mask to 255.255.255.0 (matching R1 Gi0/0's /24).",
            "remediation_check": {"device": "PC1", "interface": "eth0", "field": "mask", "expected": "255.255.255.0"},
            "verification": "ping 192.168.10.1 from PC1 succeeds (5/5).",
            "verify_check": {"device": "PC1", "dest_ip": "192.168.10.1"},
            "key_commands": ["show ip interface brief"],
        },
        "xp_reward": 90,
        "is_free_tier": True,
    },

    # ------------------------------------------------------------------
    "inc-004-missing-default-route": {
        "title": "Users Cannot Reach the Application Server",
        "difficulty": "Intermediate",
        "category": "Layer 3 - Routing",
        "priority": "P2",
        "summary": "Multiple users in the branch office can reach their local gateway but cannot reach the application server at HQ.",
        "impact": "All branch-office users (represented by PC1) cannot reach the HQ application server. Local connectivity is unaffected.",
        "symptoms": [
            "ping from PC1 to the default gateway (192.168.10.1) succeeds.",
            "ping from PC1 to the application server (198.51.100.10) fails with 'Network unreachable'.",
            "The WAN link between R1 and R2 is up.",
        ],
        "learning_objectives": [
            "Understand how a router chooses a next hop from its routing table.",
            "Practice configuring and verifying a default static route.",
        ],
        "topology": {
            "nodes": [
                {"id": "PC1", "label": "PC1", "type": "pc"},
                {"id": "SW1", "label": "SW1", "type": "switch"},
                {"id": "R1", "label": "R1 (Branch)", "type": "router"},
                {"id": "R2", "label": "R2 (HQ)", "type": "router"},
                {"id": "Server1", "label": "App Server", "type": "server"},
            ],
            "edges": [
                {"from": "PC1", "to": "SW1", "from_if": "eth0", "to_if": "Fa0/5"},
                {"from": "SW1", "to": "R1", "from_if": "Gi0/1", "to_if": "Gi0/0"},
                {"from": "R1", "to": "R2", "from_if": "Gi0/1", "to_if": "Gi0/0"},
                {"from": "R2", "to": "Server1", "from_if": "Gi0/1", "to_if": "eth0"},
            ],
        },
        "initial_state": {
            "devices": {
                "PC1": _pc("192.168.10.20", "255.255.255.0", "192.168.10.1", "AAAA.BBBB.0004"),
                "SW1": {
                    "kind": "switch",
                    "vlans": {"10": "DATA"},
                    "interfaces": {
                        "Fa0/5": {"admin_status": "up", "status": "up", "mode": "access", "access_vlan": 10},
                        "Gi0/1": {"admin_status": "up", "status": "up", "mode": "access", "access_vlan": 10},
                    },
                },
                "R1": {
                    "kind": "router",
                    "interfaces": {
                        "Gi0/0": {"admin_status": "up", "status": "up", "ip": "192.168.10.1", "mask": "255.255.255.0", "mac": "CCCC.DDDD.0004"},
                        "Gi0/1": {"admin_status": "up", "status": "up", "ip": "203.0.113.1", "mask": "255.255.255.252"},
                    },
                    "static_routes": [],  # FAULT: no default route toward R2/HQ
                    "ospf": {"enabled": False},
                },
                "R2": {
                    "kind": "router",
                    "interfaces": {
                        "Gi0/0": {"admin_status": "up", "status": "up", "ip": "203.0.113.2", "mask": "255.255.255.252"},
                        "Gi0/1": {"admin_status": "up", "status": "up", "ip": "198.51.100.1", "mask": "255.255.255.0"},
                    },
                    "static_routes": [{"network": "192.168.10.0", "mask": "255.255.255.0", "next_hop": "203.0.113.1"}],
                    "ospf": {"enabled": False},
                },
                "Server1": _server("198.51.100.10", "255.255.255.0", "198.51.100.1", "EEEE.FFFF.0004"),
            },
            "links": [
                {"a_device": "PC1", "a_if": "eth0", "b_device": "SW1", "b_if": "Fa0/5"},
                {"a_device": "SW1", "a_if": "Gi0/1", "b_device": "R1", "b_if": "Gi0/0"},
                {"a_device": "R1", "a_if": "Gi0/1", "b_device": "R2", "b_if": "Gi0/0"},
                {"a_device": "R2", "a_if": "Gi0/1", "b_device": "Server1", "b_if": "eth0"},
            ],
        },
        "answer_key": {
            "root_cause": "R1 has no default route (or static route) toward the 198.51.100.0/24 server subnet, so it has nowhere to forward traffic destined for the HQ application server.",
            "root_cause_keywords": ["default route", "missing route", "no route", "198.51.100"],
            "correct_remediation": "On R1, add 'ip route 0.0.0.0 0.0.0.0 203.0.113.2' (a default route via R2).",
            "remediation_check": {"device": "R1", "static_route": {"network": "0.0.0.0", "mask": "0.0.0.0", "next_hop": "203.0.113.2"}},
            "verification": "ping 198.51.100.10 from PC1 succeeds (5/5).",
            "verify_check": {"device": "PC1", "dest_ip": "198.51.100.10"},
            "key_commands": ["show ip route", "ping"],
        },
        "xp_reward": 130,
        "is_free_tier": False,
    },

    # ------------------------------------------------------------------
    "inc-005-ospf-adjacency": {
        "title": "OSPF Neighbor Adjacency Not Forming",
        "difficulty": "Advanced",
        "category": "Routing - OSPF",
        "priority": "P2",
        "summary": "After a change window last night, the branch office lost access to the HQ application server over the OSPF-routed WAN link.",
        "impact": "All branch-office users (represented by PC1) cannot reach the HQ application server. The WAN link itself is up.",
        "symptoms": [
            "ping from PC1 to the default gateway (192.168.10.1) succeeds.",
            "ping from PC1 to the application server (172.16.0.10) fails with 'Network unreachable'.",
            "'show ip ospf neighbor' on R1 shows no neighbors.",
        ],
        "learning_objectives": [
            "Understand OSPF adjacency requirements (area, timers, subnet).",
            "Practice diagnosing routing protocol failures rather than assuming a cabling issue.",
        ],
        "topology": {
            "nodes": [
                {"id": "PC1", "label": "PC1", "type": "pc"},
                {"id": "SW1", "label": "SW1", "type": "switch"},
                {"id": "R1", "label": "R1 (Branch)", "type": "router"},
                {"id": "R2", "label": "R2 (HQ)", "type": "router"},
                {"id": "Server1", "label": "App Server", "type": "server"},
            ],
            "edges": [
                {"from": "PC1", "to": "SW1", "from_if": "eth0", "to_if": "Fa0/5"},
                {"from": "SW1", "to": "R1", "from_if": "Gi0/1", "to_if": "Gi0/0"},
                {"from": "R1", "to": "R2", "from_if": "Gi0/1", "to_if": "Gi0/0"},
                {"from": "R2", "to": "Server1", "from_if": "Gi0/1", "to_if": "eth0"},
            ],
        },
        "initial_state": {
            "devices": {
                "PC1": _pc("192.168.10.20", "255.255.255.0", "192.168.10.1", "AAAA.BBBB.0005"),
                "SW1": {
                    "kind": "switch",
                    "vlans": {"10": "DATA"},
                    "interfaces": {
                        "Fa0/5": {"admin_status": "up", "status": "up", "mode": "access", "access_vlan": 10},
                        "Gi0/1": {"admin_status": "up", "status": "up", "mode": "access", "access_vlan": 10},
                    },
                },
                "R1": {
                    "kind": "router",
                    "interfaces": {
                        "Gi0/0": {"admin_status": "up", "status": "up", "ip": "192.168.10.1", "mask": "255.255.255.0", "mac": "CCCC.DDDD.0005"},
                        "Gi0/1": {"admin_status": "up", "status": "up", "ip": "10.0.0.1", "mask": "255.255.255.252", "ospf_area": 0},
                    },
                    "static_routes": [],
                    "ospf": {"enabled": True, "process_id": 1, "router_id": "1.1.1.1"},
                },
                "R2": {
                    "kind": "router",
                    "interfaces": {
                        "Gi0/0": {"admin_status": "up", "status": "up", "ip": "10.0.0.2", "mask": "255.255.255.252", "ospf_area": 1},  # FAULT: should be area 0
                        "Gi0/1": {"admin_status": "up", "status": "up", "ip": "172.16.0.1", "mask": "255.255.255.0", "ospf_area": 0},
                    },
                    "static_routes": [],
                    "ospf": {"enabled": True, "process_id": 1, "router_id": "2.2.2.2"},
                },
                "Server1": _server("172.16.0.10", "255.255.255.0", "172.16.0.1", "EEEE.FFFF.0005"),
            },
            "links": [
                {"a_device": "PC1", "a_if": "eth0", "b_device": "SW1", "b_if": "Fa0/5"},
                {"a_device": "SW1", "a_if": "Gi0/1", "b_device": "R1", "b_if": "Gi0/0"},
                {"a_device": "R1", "a_if": "Gi0/1", "b_device": "R2", "b_if": "Gi0/0"},
                {"a_device": "R2", "a_if": "Gi0/1", "b_device": "Server1", "b_if": "eth0"},
            ],
        },
        "answer_key": {
            "root_cause": "R2's Gi0/0 (the R1-R2 WAN link) is configured in OSPF area 1 while R1's Gi0/1 is in area 0. The area mismatch prevents the OSPF adjacency from forming, so R1 never learns the 172.16.0.0/24 route to the server.",
            "root_cause_keywords": ["ospf", "area mismatch", "area 1", "area 0", "adjacency"],
            "correct_remediation": "On R2, enter interface Gi0/0 and issue 'ip ospf area 0' to match R1.",
            "remediation_check": {"device": "R2", "interface": "Gi0/0", "field": "ospf_area", "expected": 0},
            "verification": "'show ip ospf neighbor' on R1 shows R2 in FULL state, and ping 172.16.0.10 from PC1 succeeds (5/5).",
            "verify_check": {"device": "PC1", "dest_ip": "172.16.0.10"},
            "key_commands": ["show ip ospf neighbor", "show ip route", "show running-config"],
        },
        "xp_reward": 160,
        "is_free_tier": False,
    },
}


def list_incident_slugs() -> list[str]:
    return list(INCIDENTS.keys())


def get_incident_definition(slug: str) -> dict | None:
    return INCIDENTS.get(slug)
