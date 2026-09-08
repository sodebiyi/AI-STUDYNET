import copy

from app.simulation import cli as cli_engine
from app.simulation.incidents import get_incident_definition


def test_show_vlan_brief_reveals_the_fault():
    inc = get_incident_definition("inc-001-vlan-mismatch")
    state = copy.deepcopy(inc["initial_state"])
    result = cli_engine.run_command(state, "SW1", "show vlan brief")
    assert "Fa0/5" not in result.output.split("\n")[1]  # Fa0/5 should NOT be listed under VLAN 10 (it's on VLAN 20)


def test_cli_config_sequence_fixes_vlan():
    inc = get_incident_definition("inc-001-vlan-mismatch")
    state = copy.deepcopy(inc["initial_state"])

    assert cli_engine.run_command(state, "SW1", "configure terminal").output.endswith("(config)#")
    assert cli_engine.run_command(state, "SW1", "interface Fa0/5").output.endswith("(config-if)#")
    result = cli_engine.run_command(state, "SW1", "switchport access vlan 10")
    assert result.mutated is True
    assert state["devices"]["SW1"]["interfaces"]["Fa0/5"]["access_vlan"] == 10


def test_cli_no_shutdown_fixes_interface():
    inc = get_incident_definition("inc-002-interface-down")
    state = copy.deepcopy(inc["initial_state"])

    cli_engine.run_command(state, "SW1", "configure terminal")
    cli_engine.run_command(state, "SW1", "interface Fa0/5")
    result = cli_engine.run_command(state, "SW1", "no shutdown")
    assert result.mutated is True
    assert state["devices"]["SW1"]["interfaces"]["Fa0/5"]["admin_status"] == "up"
    # Line protocol must also come up (there's a real link to PC1) or the
    # interface would still fail the ping/CLI-visible "up/up" check.
    assert state["devices"]["SW1"]["interfaces"]["Fa0/5"]["status"] == "up"


def test_invalid_command_returns_cisco_style_error():
    inc = get_incident_definition("inc-001-vlan-mismatch")
    state = copy.deepcopy(inc["initial_state"])
    result = cli_engine.run_command(state, "SW1", "make me a sandwich")
    assert result.output.startswith("% Invalid input")
    assert result.was_useful is False


def test_ping_command_reports_failure_realistically():
    inc = get_incident_definition("inc-002-interface-down")
    state = copy.deepcopy(inc["initial_state"])
    result = cli_engine.run_command(state, "PC1", "ping 192.168.10.1")
    assert "Success rate is 0 percent" in result.output


def test_show_ip_ospf_neighbor_empty_when_area_mismatched():
    inc = get_incident_definition("inc-005-ospf-adjacency")
    state = copy.deepcopy(inc["initial_state"])
    result = cli_engine.run_command(state, "R1", "show ip ospf neighbor")
    assert "no OSPF neighbors" in result.output
