import copy

from app.simulation import engine
from app.simulation.incidents import get_incident_definition


def test_vlan_mismatch_blocks_ping_and_fix_resolves_it():
    inc = get_incident_definition("inc-001-vlan-mismatch")
    state = copy.deepcopy(inc["initial_state"])

    result = engine.attempt_ping(state, "PC1", "192.168.10.1")
    assert result.success is False
    assert result.failure_layer == "layer2"

    # Apply the correct remediation directly against state.
    state["devices"]["SW1"]["interfaces"]["Fa0/5"]["access_vlan"] = 10
    result = engine.attempt_ping(state, "PC1", "192.168.10.1")
    assert result.success is True


def test_interface_down_blocks_ping_and_no_shutdown_resolves_it():
    inc = get_incident_definition("inc-002-interface-down")
    state = copy.deepcopy(inc["initial_state"])

    result = engine.attempt_ping(state, "PC1", "192.168.10.1")
    assert result.success is False
    assert result.failure_layer == "layer1"

    state["devices"]["SW1"]["interfaces"]["Fa0/5"]["admin_status"] = "up"
    state["devices"]["SW1"]["interfaces"]["Fa0/5"]["status"] = "up"
    result = engine.attempt_ping(state, "PC1", "192.168.10.1")
    assert result.success is True


def test_wrong_subnet_mask_blocks_ping():
    inc = get_incident_definition("inc-003-wrong-ip")
    state = copy.deepcopy(inc["initial_state"])

    result = engine.attempt_ping(state, "PC1", "192.168.10.1")
    assert result.success is False
    assert result.failure_layer == "layer3"

    state["devices"]["PC1"]["interfaces"]["eth0"]["mask"] = "255.255.255.0"
    result = engine.attempt_ping(state, "PC1", "192.168.10.1")
    assert result.success is True


def test_missing_default_route_blocks_ping_to_remote_server():
    inc = get_incident_definition("inc-004-missing-default-route")
    state = copy.deepcopy(inc["initial_state"])

    result = engine.attempt_ping(state, "PC1", "198.51.100.10")
    assert result.success is False
    assert result.failure_layer == "layer3"

    state["devices"]["R1"]["static_routes"].append({"network": "0.0.0.0", "mask": "0.0.0.0", "next_hop": "203.0.113.2"})
    result = engine.attempt_ping(state, "PC1", "198.51.100.10")
    assert result.success is True


def test_ospf_area_mismatch_blocks_adjacency_and_route():
    inc = get_incident_definition("inc-005-ospf-adjacency")
    state = copy.deepcopy(inc["initial_state"])

    up, reason = engine.ospf_adjacency_up(state, "R1", "Gi0/1", "R2", "Gi0/0")
    assert up is False
    assert "area" in reason.lower()

    result = engine.attempt_ping(state, "PC1", "172.16.0.10")
    assert result.success is False

    state["devices"]["R2"]["interfaces"]["Gi0/0"]["ospf_area"] = 0
    up, _ = engine.ospf_adjacency_up(state, "R1", "Gi0/1", "R2", "Gi0/0")
    assert up is True

    result = engine.attempt_ping(state, "PC1", "172.16.0.10")
    assert result.success is True
