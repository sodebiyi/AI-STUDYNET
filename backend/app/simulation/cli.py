"""
Simulated Cisco-style CLI. Parses a single command line against a device's
current simulated state and returns realistic show-command output, or
mutates state for supported configuration commands.

Only the commands needed to investigate and fix the MVP incidents are
implemented (per the product spec: "Do not make every command functional
initially. Prioritise commands necessary for the incident."). Unrecognised
commands return a realistic Cisco "% Invalid input" error rather than
silently doing nothing, so the CLI always feels real.

Per-attempt CLI mode (exec / config / config-if) is tracked in
state["_cli_context"][device] so that `configure terminal` -> `interface X`
-> `switchport access vlan 10` works as a sequence of separate API calls.
"""
from __future__ import annotations

from app.simulation import engine


class CliResult:
    def __init__(self, output: str, mutated: bool = False, was_useful: bool = True):
        self.output = output
        self.mutated = mutated
        self.was_useful = was_useful


SWITCH_ONLY_COMMANDS = {
    "show vlan brief", "show vlan", "show interfaces trunk", "show mac address-table",
    "show spanning-tree", "show etherchannel summary",
}
ROUTER_ONLY_PREFIXES = ("show ip route", "show ip ospf neighbor", "show ip bgp")


def _kind_error(device: str, dev: dict, needed: str) -> str:
    return (
        f"% Invalid input detected at '^' marker.\n"
        f"% '{device}' is a {dev.get('kind', 'device')}; this command is only available on a {needed}."
    )


def _ctx(state: dict, device: str) -> dict:
    state.setdefault("_cli_context", {})
    state["_cli_context"].setdefault(device, {"mode": "exec", "interface": None})
    return state["_cli_context"][device]


def run_command(state: dict, device: str, raw_command: str) -> CliResult:
    dev = engine.get_device(state, device)
    if dev is None:
        return CliResult(f"% Unknown device: {device}", was_useful=False)

    cmd = raw_command.strip()
    if not cmd:
        return CliResult("", was_useful=False)

    ctx = _ctx(state, device)
    lower = cmd.lower()
    parts = cmd.split()

    # --- mode transitions -------------------------------------------------
    if lower in ("configure terminal", "conf t", "config t"):
        ctx["mode"] = "config"
        return CliResult(f"{device}(config)#", was_useful=True)

    if lower.startswith("interface ") and ctx["mode"] in ("config",):
        ifname = _normalize_ifname(cmd[len("interface "):].strip())
        if engine.get_iface(state, device, ifname) is None:
            return CliResult(f"% Invalid interface {ifname}", was_useful=False)
        ctx["mode"] = "config-if"
        ctx["interface"] = ifname
        return CliResult(f"{device}(config-if)#", was_useful=True)

    if lower in ("exit",):
        ctx["mode"] = "config" if ctx["mode"] == "config-if" else "exec"
        ctx["interface"] = None
        return CliResult(f"{device}#", was_useful=False)

    if lower in ("end",):
        ctx["mode"] = "exec"
        ctx["interface"] = None
        return CliResult(f"{device}#", was_useful=False)

    # --- config-if level commands ------------------------------------------
    if ctx["mode"] == "config-if":
        ifname = ctx["interface"]
        iface = engine.get_iface(state, device, ifname)

        if lower == "no shutdown":
            iface["admin_status"] = "up"
            # Line protocol comes up too, IF there's actually a physical
            # link on the other end (a real cable/peer) — "no shutdown"
            # alone can't fix a genuinely disconnected cable.
            has_physical_link = engine.find_link_peer(state, device, ifname) is not None
            if has_physical_link:
                iface["status"] = "up"
                return CliResult(
                    f"%LINK-3-UPDOWN: Interface {ifname}, changed state to up\n"
                    f"%LINEPROTO-5-UPDOWN: Line protocol on Interface {ifname}, changed state to up",
                    mutated=True,
                )
            return CliResult(f"%LINK-3-UPDOWN: Interface {ifname}, changed state to up (line protocol still down — check cabling)", mutated=True)

        if lower == "shutdown":
            iface["admin_status"] = "down"
            iface["status"] = "down"
            return CliResult(f"%LINK-5-CHANGED: Interface {ifname}, changed state to administratively down", mutated=True)

        if lower.startswith("switchport access vlan "):
            try:
                vlan = int(parts[-1])
            except ValueError:
                return CliResult("% Invalid VLAN id", was_useful=False)
            vlans = engine.get_device(state, device).get("vlans", {})
            if str(vlan) not in vlans:
                return CliResult(f"% VLAN {vlan} does not exist. Create it first with 'vlan {vlan}'.", was_useful=False)
            iface["mode"] = "access"
            iface["access_vlan"] = vlan
            return CliResult(f"Interface {ifname} access VLAN set to {vlan}", mutated=True)

        if lower.startswith("ip address "):
            try:
                _, _, ip, mask = cmd.split()
            except ValueError:
                return CliResult("% Incomplete command.", was_useful=False)
            iface["ip"] = ip
            iface["mask"] = mask
            return CliResult(f"Interface {ifname} IP address set to {ip} {mask}", mutated=True)

        if lower.startswith("ip ospf area "):
            try:
                area = int(parts[-1])
            except ValueError:
                return CliResult("% Invalid area id", was_useful=False)
            iface["ospf_area"] = area
            return CliResult(f"Interface {ifname} added to OSPF area {area}", mutated=True)

        return CliResult(f"% Invalid input detected at '^' marker (command '{cmd}' not supported in interface config mode).", was_useful=False)

    # --- global config level commands --------------------------------------
    if ctx["mode"] == "config":
        if lower.startswith("ip route "):
            try:
                _, _, network, mask, next_hop = cmd.split()
            except ValueError:
                return CliResult("% Incomplete command. Usage: ip route <network> <mask> <next-hop>", was_useful=False)
            dev.setdefault("static_routes", [])
            dev["static_routes"].append({"network": network, "mask": mask, "next_hop": next_hop})
            return CliResult(f"Static route added: {network} {mask} -> {next_hop}", mutated=True)

        if lower.startswith("router ospf "):
            dev.setdefault("ospf", {})["enabled"] = True
            return CliResult(f"{device}(config-router)#", was_useful=True)

        if lower.startswith("vlan "):
            try:
                vlan = int(parts[-1])
            except ValueError:
                return CliResult("% Invalid VLAN id", was_useful=False)
            dev.setdefault("vlans", {})[str(vlan)] = dev.get("vlans", {}).get(str(vlan), f"VLAN{vlan:04d}")
            return CliResult(f"VLAN {vlan} created.", mutated=True)

        return CliResult(f"% Invalid input detected at '^' marker (command '{cmd}' not supported in config mode).", was_useful=False)

    # --- exec-level (show / ping / traceroute) ------------------------------
    kind = dev.get("kind")

    if lower in SWITCH_ONLY_COMMANDS and kind != "switch":
        return CliResult(_kind_error(device, dev, "switch"), was_useful=False)
    if lower.startswith(ROUTER_ONLY_PREFIXES) and kind != "router":
        return CliResult(_kind_error(device, dev, "router"), was_useful=False)

    if lower == "show ip interface brief" or lower == "sh ip int brief" or lower == "show ip int brief":
        return CliResult(_show_ip_interface_brief(dev))

    if lower == "show running-config" or lower == "show run" or lower == "sh run":
        return CliResult(_show_running_config(device, dev))

    if lower == "show startup-config":
        return CliResult(_show_running_config(device, dev) + "\n! (startup-config matches running-config in this simulation)")

    if lower == "show vlan brief" or lower == "show vlan":
        return CliResult(_show_vlan_brief(dev))

    if lower == "show interfaces trunk":
        return CliResult(_show_interfaces_trunk(dev))

    if lower.startswith("show interfaces") or lower.startswith("show interface "):
        target = cmd.split(None, 2)[2] if len(parts) > 2 else None
        return CliResult(_show_interfaces(dev, target))

    if lower == "show mac address-table":
        return CliResult(_show_mac_address_table(state, device, dev))

    if lower == "show spanning-tree":
        return CliResult(_show_spanning_tree(dev))

    if lower == "show etherchannel summary":
        return CliResult("No port channels configured.\n")

    if lower == "show ip route" or lower == "show ip route ":
        return CliResult(_show_ip_route(state, device))

    if lower == "show ip ospf neighbor":
        return CliResult(_show_ospf_neighbor(state, device))

    if lower.startswith("show ip bgp"):
        return CliResult("% BGP is not configured on this device.", was_useful=False)

    if lower == "show arp":
        return CliResult(_show_arp(state, device, dev))

    if lower in ("show cdp neighbors", "show lldp neighbors"):
        return CliResult(_show_neighbors(state, device))

    if lower.startswith("ping "):
        dest = parts[-1]
        result = engine.attempt_ping(state, device, dest)
        return CliResult(f"Type escape sequence to abort.\n{result.output}", was_useful=True)

    if lower.startswith("traceroute "):
        dest = parts[-1]
        result = engine.attempt_ping(state, device, dest)
        if result.success:
            hops = "\n".join(f" {i+1}  {h}  1 msec" for i, h in enumerate(result.path[1:]))
            return CliResult(f"Tracing route to {dest}\n{hops}")
        return CliResult(f"Tracing route to {dest}\n * * *\nRequest timed out at hop toward {dest} ({result.failure_layer}).")

    return CliResult(f"% Invalid input detected at '^' marker (command '{cmd}' not recognised).", was_useful=False)


# --------------------------------------------------------------------------
# show-command renderers
# --------------------------------------------------------------------------

def _normalize_ifname(raw: str) -> str:
    """Accept common Cisco abbreviations (fa0/5, Fa0/5, gi0/1) as typed."""
    return raw.strip()


def _status_text(iface: dict) -> tuple[str, str]:
    admin = "up" if iface.get("admin_status") == "up" else "administratively down"
    line = "up" if iface.get("status") == "up" and iface.get("admin_status") == "up" else "down"
    return admin, line


def _show_ip_interface_brief(dev: dict) -> str:
    lines = [f"{'Interface':<18}{'IP-Address':<16}{'OK?':<5}{'Status':<24}{'Protocol'}"]
    for name, iface in dev.get("interfaces", {}).items():
        ip = iface.get("ip") or "unassigned"
        admin, line = _status_text(iface)
        lines.append(f"{name:<18}{ip:<16}{'YES':<5}{admin:<24}{line}")
    return "\n".join(lines)


def _show_running_config(device: str, dev: dict) -> str:
    out = [f"Building configuration...\n", f"! Current configuration for {device}", "!"]
    for name, iface in dev.get("interfaces", {}).items():
        out.append(f"interface {name}")
        if iface.get("mode") == "access":
            out.append(f" switchport mode access")
            out.append(f" switchport access vlan {iface.get('access_vlan')}")
        elif iface.get("mode") == "trunk":
            out.append(f" switchport mode trunk")
            out.append(f" switchport trunk allowed vlan {','.join(str(v) for v in iface.get('trunk_allowed_vlans', []))}")
        if iface.get("ip"):
            out.append(f" ip address {iface['ip']} {iface['mask']}")
        if iface.get("ospf_area") is not None:
            out.append(f" ip ospf area {iface['ospf_area']}")
        if iface.get("admin_status") != "up":
            out.append(" shutdown")
        out.append("!")
    for sr in dev.get("static_routes", []):
        out.append(f"ip route {sr['network']} {sr['mask']} {sr['next_hop']}")
    if dev.get("ospf", {}).get("enabled"):
        out.append(f"router ospf {dev['ospf'].get('process_id', 1)}")
    return "\n".join(out)


def _show_vlan_brief(dev: dict) -> str:
    vlans = dev.get("vlans", {})
    lines = [f"{'VLAN':<8}{'Name':<24}{'Status':<10}{'Ports'}"]
    for vid, name in vlans.items():
        ports = [ifn for ifn, i in dev.get("interfaces", {}).items() if i.get("mode") == "access" and str(i.get("access_vlan")) == str(vid)]
        lines.append(f"{vid:<8}{name:<24}{'active':<10}{', '.join(ports)}")
    return "\n".join(lines)


def _show_interfaces_trunk(dev: dict) -> str:
    lines = [f"{'Port':<12}{'Mode':<10}{'Encapsulation':<16}{'Status':<12}{'Native vlan'}"]
    for name, iface in dev.get("interfaces", {}).items():
        if iface.get("mode") == "trunk":
            lines.append(f"{name:<12}{'on':<10}{'802.1q':<16}{'trunking':<12}{iface.get('native_vlan', 1)}")
    if len(lines) == 1:
        return "No trunking interfaces found."
    lines.append("")
    lines.append(f"{'Port':<12}{'Vlans allowed on trunk'}")
    for name, iface in dev.get("interfaces", {}).items():
        if iface.get("mode") == "trunk":
            lines.append(f"{name:<12}{','.join(str(v) for v in iface.get('trunk_allowed_vlans', []))}")
    return "\n".join(lines)


def _show_interfaces(dev: dict, target: str | None) -> str:
    out = []
    items = dev.get("interfaces", {}).items()
    if target:
        items = [(k, v) for k, v in items if k.lower() == target.lower()]
        if not items:
            return f"% Invalid interface {target}"
    for name, iface in items:
        admin, line = _status_text(iface)
        out.append(f"{name} is {line}, line protocol is {line} ({admin})")
        if iface.get("ip"):
            out.append(f"  Internet address is {iface['ip']}/{_prefixlen(iface.get('mask'))}")
        out.append(f"  MTU 1500 bytes, BW 1000000 Kbit, DLY 10 usec")
        out.append("  0 input errors, 0 CRC, 0 frame, 0 overrun")
        out.append("")
    return "\n".join(out)


def _prefixlen(mask: str | None) -> int:
    if not mask:
        return 0
    return sum(bin(int(o)).count("1") for o in mask.split("."))


def _show_mac_address_table(state: dict, device: str, dev: dict) -> str:
    lines = [f"{'Vlan':<8}{'Mac Address':<20}{'Type':<10}{'Ports'}"]
    for name, iface in dev.get("interfaces", {}).items():
        if iface.get("mode") != "access":
            continue
        peer = engine.find_link_peer(state, device, name)
        if not peer:
            continue
        peer_iface = engine.get_iface(state, peer[0], peer[1])
        mac = (peer_iface or {}).get("mac")
        if mac:
            lines.append(f"{iface.get('access_vlan'):<8}{mac:<20}{'DYNAMIC':<10}{name}")
    return "\n".join(lines)


def _show_spanning_tree(dev: dict) -> str:
    lines = ["VLAN0001"]
    lines.append("  Spanning tree enabled protocol ieee")
    for name, iface in dev.get("interfaces", {}).items():
        if iface.get("mode") in ("access", "trunk"):
            state_txt = "FWD" if iface.get("admin_status") == "up" else "BLK"
            lines.append(f"{name:<12}Desg {state_txt}  4  128.1  P2p")
    return "\n".join(lines)


def _show_ip_route(state: dict, device: str) -> str:
    routes = engine.build_route_table(state, device)
    lines = ["Codes: C - connected, S - static, O - OSPF", ""]
    for r in routes:
        prefix = _prefixlen(r["mask"])
        if r["code"] == "C":
            lines.append(f"C    {r['network']}/{prefix} is directly connected, {r['iface']}")
        elif r["code"] == "S":
            lines.append(f"S    {r['network']}/{prefix} [1/0] via {r['next_hop']}")
        else:
            lines.append(f"O    {r['network']}/{prefix} [110/2] via {r['next_hop']}, {r['iface']}")
    if len(lines) == 2:
        lines.append("(no routes)")
    return "\n".join(lines)


def _show_ospf_neighbor(state: dict, device: str) -> str:
    neighbors = engine.ospf_neighbors(state, device)
    if not neighbors:
        return "(no OSPF neighbors — adjacency not established. Check area, timers, and that OSPF is enabled on the correct interface.)"
    lines = [f"{'Neighbor ID':<16}{'Pri':<6}{'State':<14}{'Address':<16}{'Interface'}"]
    for n in neighbors:
        lines.append(f"{n['neighbor_id']:<16}{'1':<6}{n['state']:<14}{n['neighbor_ip']:<16}{n['interface']}")
    return "\n".join(lines)


def _show_arp(state: dict, device: str, dev: dict) -> str:
    lines = [f"{'Protocol':<10}{'Address':<16}{'Age':<8}{'Hardware Addr':<16}{'Interface'}"]
    for name, iface in dev.get("interfaces", {}).items():
        peer = engine.find_link_peer(state, device, name)
        if not peer:
            continue
        peer_iface = engine.get_iface(state, peer[0], peer[1])
        if peer_iface and peer_iface.get("ip") and peer_iface.get("mac"):
            lines.append(f"{'Internet':<10}{peer_iface['ip']:<16}{'0':<8}{peer_iface['mac']:<16}{name}")
    return "\n".join(lines)


def _show_neighbors(state: dict, device: str) -> str:
    dev = engine.get_device(state, device)
    lines = [f"{'Device ID':<16}{'Local Intrfce':<16}{'Capability':<14}{'Platform':<12}{'Port ID'}"]
    for name in dev.get("interfaces", {}):
        peer = engine.find_link_peer(state, device, name)
        if not peer:
            continue
        peer_device, peer_if = peer
        peer_kind = engine.get_device(state, peer_device).get("kind", "?")
        lines.append(f"{peer_device:<16}{name:<16}{peer_kind[:1].upper():<14}{peer_kind:<12}{peer_if}")
    return "\n".join(lines)
