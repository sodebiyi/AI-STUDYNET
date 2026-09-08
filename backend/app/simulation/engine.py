"""
NetMentor's controlled network simulation engine.

This is NOT a packet-accurate emulator. It represents devices, interfaces,
links, VLANs, routes and OSPF adjacencies as structured JSON state, and
evaluates *outcomes* (does a ping succeed, what does a route table look
like, is an OSPF adjacency up) by walking that structured state. That
keeps it fast, deterministic, and gradeable, while still forcing the
student to reason about real Layer 1/2/3 behaviour.

The state dict shape (see app/simulation/incidents.py for concrete examples):

{
  "devices": {
    "<name>": {
      "kind": "pc" | "switch" | "router" | "server",
      "interfaces": {
        "<ifname>": {
          "admin_status": "up" | "down",     # shutdown / no shutdown
          "status": "up" | "down",           # line protocol (cable etc.)
          "mode": "access" | "trunk" | None, # switch ports only
          "access_vlan": int | None,
          "trunk_allowed_vlans": [int] | None,
          "native_vlan": int | None,
          "ip": "a.b.c.d" | None,
          "mask": "a.b.c.d" | None,
          "gateway": "a.b.c.d" | None,       # end devices only
          "mac": "AAAA.BBBB.CCCC" | None,
          "ospf_area": int | None,           # routers: area this iface is in
        }
      },
      "vlans": {"10": "DATA", ...},          # switches only
      "static_routes": [{"network": "0.0.0.0", "mask": "0.0.0.0", "next_hop": "..."}],
      "ospf": {"enabled": bool, "process_id": int, "router_id": "x.x.x.x"},
    }
  },
  "links": [{"a_device": "...", "a_if": "...", "b_device": "...", "b_if": "..."}]
}

This module is intentionally decoupled from FastAPI/SQLAlchemy so it can be
unit tested directly and, per the product spec, later swapped for a real
emulator (EVE-NG/GNS3/container networking) behind the same call shape:
`attempt_ping`, `run_show_command`, `apply_config_command`.
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field


MAX_HOPS = 8


# --------------------------------------------------------------------------
# Low-level state helpers
# --------------------------------------------------------------------------

def get_device(state: dict, name: str) -> dict | None:
    return state.get("devices", {}).get(name)


def get_iface(state: dict, device: str, ifname: str) -> dict | None:
    dev = get_device(state, device)
    if not dev:
        return None
    return dev.get("interfaces", {}).get(ifname)


def find_link_peer(state: dict, device: str, ifname: str) -> tuple[str, str] | None:
    for link in state.get("links", []):
        if link["a_device"] == device and link["a_if"] == ifname:
            return link["b_device"], link["b_if"]
        if link["b_device"] == device and link["b_if"] == ifname:
            return link["a_device"], link["a_if"]
    return None


def find_owner_of_ip(state: dict, ip: str) -> tuple[str, str] | None:
    for dname, dev in state.get("devices", {}).items():
        for ifname, iface in dev.get("interfaces", {}).items():
            if iface.get("ip") == ip:
                return dname, ifname
    return None


def _subnet(ip: str, mask: str) -> ipaddress.IPv4Network:
    return ipaddress.ip_network(f"{ip}/{mask}", strict=False)


def same_subnet(ip_a: str, mask_a: str, ip_b: str) -> bool:
    try:
        return ipaddress.ip_address(ip_b) in _subnet(ip_a, mask_a)
    except ValueError:
        return False


# --------------------------------------------------------------------------
# Layer 1 / Layer 2 path walking
# --------------------------------------------------------------------------

@dataclass
class HopResult:
    ok: bool
    device: str
    ifname: str | None = None
    reason: str | None = None
    layer: str | None = None


def _iface_up(iface: dict) -> bool:
    return iface.get("admin_status") == "up" and iface.get("status") == "up"


def l2_path_reachable(state: dict, start_device: str, start_if: str, target_device: str, target_if: str) -> HopResult:
    """
    Walk the physical link graph from (start_device, start_if) to
    (target_device, target_if), crossing zero or more switches, checking
    L1 (admin/line status) and L2 (VLAN access/trunk membership) at every
    hop. Returns the first failing hop, or an ok HopResult if the whole
    path is clear.
    """
    src_iface = get_iface(state, start_device, start_if)
    if src_iface is None:
        return HopResult(False, start_device, start_if, "Interface does not exist.", "layer1")
    if not _iface_up(src_iface):
        reason = "administratively down" if src_iface.get("admin_status") != "up" else "line protocol down (no cable / no signal)"
        return HopResult(False, start_device, start_if, reason, "layer1")

    # VLAN context carried onto the wire as we leave the source device.
    carried_vlan = src_iface.get("access_vlan")

    current_device, current_if = start_device, start_if
    for _ in range(MAX_HOPS):
        peer = find_link_peer(state, current_device, current_if)
        if peer is None:
            return HopResult(False, current_device, current_if, "No physical link (cable disconnected).", "layer1")
        peer_device, peer_if = peer
        peer_iface = get_iface(state, peer_device, peer_if)
        if peer_iface is None or not _iface_up(peer_iface):
            reason = "administratively down" if (peer_iface or {}).get("admin_status") != "up" else "line protocol down (no cable / no signal)"
            return HopResult(False, peer_device, peer_if, reason, "layer1")

        # VLAN check at the ingress port of the device we just arrived at,
        # only meaningful for switches.
        peer_device_kind = get_device(state, peer_device).get("kind")
        if peer_device_kind == "switch":
            mode = peer_iface.get("mode")
            if mode == "access":
                port_vlan = peer_iface.get("access_vlan")
                if carried_vlan is not None and port_vlan != carried_vlan:
                    return HopResult(
                        False, peer_device, peer_if,
                        f"VLAN mismatch: frame carries VLAN {carried_vlan}, port is access VLAN {port_vlan}.",
                        "layer2",
                    )
                carried_vlan = port_vlan
            elif mode == "trunk":
                allowed = peer_iface.get("trunk_allowed_vlans") or []
                if carried_vlan is not None and carried_vlan not in allowed:
                    return HopResult(
                        False, peer_device, peer_if,
                        f"VLAN {carried_vlan} is not permitted on trunk (allowed: {allowed}).",
                        "layer2",
                    )

            if (peer_device, peer_if) == (target_device, target_if):
                return HopResult(True, peer_device, peer_if)

            # Continue through the switch: find another interface on the
            # same device that is on the path toward the target (for our
            # simple topologies, this is any other active port carrying
            # the same VLAN toward the target's connected component).
            next_hop = _next_switch_egress(state, peer_device, peer_if, target_device, target_if, carried_vlan)
            if next_hop is None:
                return HopResult(False, peer_device, None, "No forwarding path toward destination VLAN.", "layer2")
            current_device, current_if = peer_device, next_hop
            continue

        # Reached a non-switch device (router/pc/server).
        if (peer_device, peer_if) == (target_device, target_if):
            return HopResult(True, peer_device, peer_if)
        return HopResult(False, peer_device, peer_if, "Path does not lead to destination.", "layer2")

    return HopResult(False, current_device, current_if, "Max hop count exceeded (possible loop).", "layer2")


def _next_switch_egress(state: dict, switch: str, ingress_if: str, target_device: str, target_if: str, vlan: int | None) -> str | None:
    """Forwarding heuristic: only consider ports whose VLAN configuration
    would actually carry this frame (access port on the same VLAN, or
    trunk port permitting it) — this is what makes an access-VLAN mismatch
    on the EGRESS side of a switch (not just the ingress side) correctly
    block the frame. Among those, prefer the port directly linked to the
    target device."""
    dev = get_device(state, switch)
    candidates = []
    for ifname, iface in dev.get("interfaces", {}).items():
        if ifname == ingress_if or not _iface_up(iface):
            continue
        if iface.get("mode") == "access":
            if vlan is not None and iface.get("access_vlan") != vlan:
                continue
        elif iface.get("mode") == "trunk":
            if vlan is not None and vlan not in (iface.get("trunk_allowed_vlans") or []):
                continue
        else:
            continue
        candidates.append(ifname)

    for ifname in candidates:
        peer = find_link_peer(state, switch, ifname)
        if peer == (target_device, target_if):
            return ifname
    return candidates[0] if candidates else None


# --------------------------------------------------------------------------
# OSPF adjacency + route derivation
# --------------------------------------------------------------------------

def ospf_adjacency_up(state: dict, router_a: str, if_a: str, router_b: str, if_b: str) -> tuple[bool, str | None]:
    dev_a, dev_b = get_device(state, router_a), get_device(state, router_b)
    ia, ib = get_iface(state, router_a, if_a), get_iface(state, router_b, if_b)
    if not (dev_a.get("ospf", {}).get("enabled") and dev_b.get("ospf", {}).get("enabled")):
        return False, "OSPF not enabled on both routers."
    if ia.get("ospf_area") is None or ib.get("ospf_area") is None:
        return False, "Interface not included in an OSPF network statement."
    if not (_iface_up(ia) and _iface_up(ib)):
        return False, "Link is down."
    if ia.get("ospf_area") != ib.get("ospf_area"):
        return False, f"OSPF area mismatch (area {ia.get('ospf_area')} vs area {ib.get('ospf_area')})."
    if ia.get("ospf_hello_interval", 10) != ib.get("ospf_hello_interval", 10):
        return False, "Hello/dead timer mismatch."
    return True, None


def ospf_neighbors(state: dict, router: str) -> list[dict]:
    """Compute OSPF FULL neighbors for `router` by checking every link that
    touches one of its OSPF-enabled interfaces."""
    neighbors = []
    dev = get_device(state, router)
    if not dev or not dev.get("ospf", {}).get("enabled"):
        return neighbors
    for ifname, iface in dev.get("interfaces", {}).items():
        if iface.get("ospf_area") is None:
            continue
        peer = find_link_peer(state, router, ifname)
        if not peer:
            continue
        peer_device, peer_if = peer
        peer_dev = get_device(state, peer_device)
        if peer_dev.get("kind") != "router":
            continue
        up, _reason = ospf_adjacency_up(state, router, ifname, peer_device, peer_if)
        if up:
            peer_iface = get_iface(state, peer_device, peer_if)
            neighbors.append({
                "neighbor_id": peer_dev.get("ospf", {}).get("router_id", peer_device),
                "interface": ifname,
                "neighbor_ip": peer_iface.get("ip"),
                "state": "FULL/DR" if ifname else "FULL",
            })
    return neighbors


def _router_connected_subnets(state: dict, router: str) -> list[tuple[str, str, str]]:
    """Return (network, mask, via_iface) for all up, IP-configured interfaces."""
    out = []
    dev = get_device(state, router)
    for ifname, iface in dev.get("interfaces", {}).items():
        if iface.get("ip") and _iface_up(iface):
            net = _subnet(iface["ip"], iface["mask"])
            out.append((str(net.network_address), iface["mask"], ifname))
    return out


def build_route_table(state: dict, router: str) -> list[dict]:
    """Connected + static + OSPF-derived routes, Cisco-`show ip route`-style."""
    routes = []
    dev = get_device(state, router)

    for net, mask, ifname in _router_connected_subnets(state, router):
        routes.append({"code": "C", "network": net, "mask": mask, "next_hop": None, "iface": ifname})

    for sr in dev.get("static_routes", []):
        routes.append({"code": "S", "network": sr["network"], "mask": sr["mask"], "next_hop": sr["next_hop"], "iface": None})

    for ifname, iface in dev.get("interfaces", {}).items():
        if iface.get("ospf_area") is None:
            continue
        peer = find_link_peer(state, router, ifname)
        if not peer:
            continue
        peer_device, peer_if = peer
        peer_dev = get_device(state, peer_device)
        if peer_dev.get("kind") != "router":
            continue
        up, _ = ospf_adjacency_up(state, router, ifname, peer_device, peer_if)
        if not up:
            continue
        # Adjacency is up: learn the neighbor's OTHER OSPF-enabled, non-shared subnets.
        for other_if, other_iface in peer_dev.get("interfaces", {}).items():
            if other_if == peer_if or other_iface.get("ospf_area") is None:
                continue
            if not other_iface.get("ip") or not _iface_up(other_iface):
                continue
            net = _subnet(other_iface["ip"], other_iface["mask"])
            already = any(r["network"] == str(net.network_address) for r in routes)
            if not already:
                routes.append({
                    "code": "O", "network": str(net.network_address), "mask": other_iface["mask"],
                    "next_hop": peer_iface_ip(state, peer_device, peer_if), "iface": ifname,
                })
    return routes


def peer_iface_ip(state: dict, device: str, ifname: str) -> str | None:
    iface = get_iface(state, device, ifname)
    return iface.get("ip") if iface else None


def route_lookup(state: dict, router: str, dest_ip: str) -> dict | None:
    """Longest-prefix match against this router's route table (connected + static + OSPF), falling back to a default route."""
    candidates = build_route_table(state, router)
    best = None
    best_prefix = -1
    dest = ipaddress.ip_address(dest_ip)
    for r in candidates:
        try:
            net = ipaddress.ip_network(f"{r['network']}/{r['mask']}", strict=False)
        except ValueError:
            continue
        if dest in net and net.prefixlen > best_prefix:
            best = r
            best_prefix = net.prefixlen
    return best


# --------------------------------------------------------------------------
# Ping simulation (the primary "is it fixed?" check)
# --------------------------------------------------------------------------

@dataclass
class PingResult:
    success: bool
    output: str
    failure_layer: str | None = None
    failure_reason: str | None = None
    path: list[str] = field(default_factory=list)


def attempt_ping(state: dict, src_device: str, dest_ip: str) -> PingResult:
    dev = get_device(state, src_device)
    if dev is None:
        return PingResult(False, f"% Unknown device {src_device}")

    if dev.get("kind") in ("pc", "server"):
        ifname, iface = next(iter(dev.get("interfaces", {}).items()))
        if not iface.get("ip"):
            return PingResult(False, "% No IP address configured on this host.", "layer3", "No IP address configured.")

        owner = find_owner_of_ip(state, dest_ip)
        if owner and same_subnet(iface["ip"], iface["mask"], dest_ip):
            target_device, target_if = owner
            hop = l2_path_reachable(state, src_device, ifname, target_device, target_if)
            return _render_ping(hop, [src_device, target_device])

        gateway = iface.get("gateway")
        if not gateway:
            return PingResult(False, "% No default gateway configured.", "layer3", "No default gateway configured.")
        if not same_subnet(iface["ip"], iface["mask"], gateway):
            return PingResult(
                False,
                "Sending 5, 100-byte ICMP Echos...\n"
                "Destination host unreachable.\n"
                "Success rate is 0 percent (0/5)",
                "layer3",
                f"Default gateway {gateway} is not on the host's configured subnet ({iface['ip']}/{iface['mask']}) — check the IP address/subnet mask.",
            )
        gw_device, gw_if = find_owner_of_ip(state, gateway)
        hop = l2_path_reachable(state, src_device, ifname, gw_device, gw_if)
        if not hop.ok:
            return _render_ping(hop, [src_device])
        return _route_from_router(state, gw_device, dest_ip, path=[src_device, gw_device])

    if dev.get("kind") == "router":
        return _route_from_router(state, src_device, dest_ip, path=[src_device])

    return PingResult(False, "% Unsupported source device type.")


def _route_from_router(state: dict, router: str, dest_ip: str, path: list[str], hops_left: int = MAX_HOPS) -> PingResult:
    if hops_left <= 0:
        return PingResult(False, "% Routing loop / max hops exceeded.", "layer3", "Routing loop detected.")

    owner = find_owner_of_ip(state, dest_ip)
    for net, mask, ifname in _router_connected_subnets(state, router):
        if owner and same_subnet(net, mask, dest_ip):
            target_device, target_if = owner
            hop = l2_path_reachable(state, router, ifname, target_device, target_if)
            return _render_ping(hop, path + [target_device])

    route = route_lookup(state, router, dest_ip)
    if route is None:
        return PingResult(
            False,
            "Sending 5, 100-byte ICMP Echos...\n"
            "% Network unreachable\n"
            "Success rate is 0 percent (0/5)",
            "layer3",
            f"No route to {dest_ip} in the routing table (check static routes, default route, or routing protocol adjacency).",
            path,
        )
    if route["code"] == "C":
        return PingResult(True, _ping_success_text(), path=path)

    next_hop_ip = route["next_hop"]
    if next_hop_ip is None:
        return PingResult(True, _ping_success_text(), path=path)
    next_owner = find_owner_of_ip(state, next_hop_ip)
    if not next_owner:
        return PingResult(False, "% Next hop unresolved.", "layer3", "Next hop not reachable.", path)
    next_router, next_if = next_owner
    return _route_from_router(state, next_router, dest_ip, path + [next_router], hops_left - 1)


def _ping_success_text() -> str:
    return (
        "Sending 5, 100-byte ICMP Echos...\n"
        "!!!!!\n"
        "Success rate is 100 percent (5/5), round-trip min/avg/max = 1/2/4 ms"
    )


def _render_ping(hop: HopResult, path: list[str]) -> PingResult:
    if hop.ok:
        return PingResult(True, _ping_success_text(), path=path)
    return PingResult(
        False,
        "Sending 5, 100-byte ICMP Echos...\n"
        ".....\n"
        "Success rate is 0 percent (0/5)",
        hop.layer,
        hop.reason,
        path,
    )
