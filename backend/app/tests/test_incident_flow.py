"""
End-to-end walkthrough of the sample incident from the product spec
(section 24 / 29): register -> login -> dashboard -> list incidents ->
start attempt -> CLI investigation -> AI coach guidance -> diagnosis ->
CLI remediation -> verification -> score -> skill profile update.
"""


def test_full_vlan_incident_walkthrough(auth_client):
    client = auth_client

    # Dashboard is reachable for a brand-new user with zero history.
    dash = client.get("/api/v1/dashboard")
    assert dash.status_code == 200
    assert dash.json()["incidents_solved"] == 0

    # List incidents, pick the VLAN one.
    incidents = client.get("/api/v1/incidents").json()
    inc = next(i for i in incidents if i["slug"] == "inc-001-vlan-mismatch")
    assert inc["is_free_tier"] is True

    # Incident detail never exposes the answer key.
    detail = client.get(f"/api/v1/incidents/{inc['id']}").json()
    assert "answer_key" not in detail
    assert "initial_state" not in detail

    # Start an attempt.
    start = client.post("/api/v1/incidents/attempts", json={"incident_id": inc["id"]})
    assert start.status_code == 201
    attempt_id = start.json()["id"]

    # Student's first ping fails.
    ping1 = client.post(f"/api/v1/incidents/attempts/{attempt_id}/cli", json={"device": "PC1", "command": "ping 192.168.10.1"})
    assert "Success rate is 0 percent" in ping1.json()["output"]

    # Coach won't just give the answer.
    coach1 = client.post(f"/api/v1/incidents/attempts/{attempt_id}/coach", json={"message": "what's wrong?"})
    assert "root cause" not in coach1.json()["reply"].lower() or "won't just give you" in coach1.json()["reply"].lower()

    # Investigate Layer 1.
    client.post(f"/api/v1/incidents/attempts/{attempt_id}/cli", json={"device": "PC1", "command": "show ip interface brief"})
    # Investigate Layer 2 — this reveals the fault.
    vlan_check = client.post(f"/api/v1/incidents/attempts/{attempt_id}/cli", json={"device": "SW1", "command": "show vlan brief"})
    assert vlan_check.status_code == 200

    # Ask for a hint to make sure the hint pipeline works end-to-end too.
    hint = client.post(f"/api/v1/incidents/attempts/{attempt_id}/hint")
    assert hint.status_code == 200
    assert "Hint (1/3)" in hint.json()["hint"]

    # Submit correct diagnosis.
    diagnosis = client.post(
        f"/api/v1/incidents/attempts/{attempt_id}/diagnose",
        json={"root_cause_statement": "The access port Fa0/5 on SW1 is set to VLAN 20 instead of VLAN 10"},
    )
    assert diagnosis.json()["matched"] is True

    # Apply the fix via the CLI.
    client.post(f"/api/v1/incidents/attempts/{attempt_id}/cli", json={"device": "SW1", "command": "configure terminal"})
    client.post(f"/api/v1/incidents/attempts/{attempt_id}/cli", json={"device": "SW1", "command": "interface Fa0/5"})
    fix = client.post(f"/api/v1/incidents/attempts/{attempt_id}/cli", json={"device": "SW1", "command": "switchport access vlan 10"})
    assert fix.status_code == 200

    # Verify — this should now succeed and resolve the attempt.
    verify = client.post(f"/api/v1/incidents/attempts/{attempt_id}/verify", json={"device": "PC1", "command": "ping 192.168.10.1"})
    assert verify.status_code == 200
    body = verify.json()
    assert body["attempt"]["status"] == "resolved"
    assert body["attempt"]["score_overall"] is not None
    assert body["attempt"]["score_overall"] > 0
    assert "root_cause" in body

    # Dashboard and readiness now reflect the resolved incident.
    dash2 = client.get("/api/v1/dashboard").json()
    assert dash2["incidents_solved"] == 1

    readiness = client.get("/api/v1/readiness")
    assert readiness.status_code == 200
    assert "level" in readiness.json()


def test_full_interface_down_incident_walkthrough(auth_client):
    """Regression test for a real bug caught via manual browser testing:
    'no shutdown' must also bring the line protocol (status) up, not just
    admin_status, or verification would fail forever even after the
    'correct' fix was applied."""
    client = auth_client
    incidents = client.get("/api/v1/incidents").json()
    inc = next(i for i in incidents if i["slug"] == "inc-002-interface-down")
    attempt_id = client.post("/api/v1/incidents/attempts", json={"incident_id": inc["id"]}).json()["id"]

    client.post(f"/api/v1/incidents/attempts/{attempt_id}/cli", json={"device": "SW1", "command": "configure terminal"})
    client.post(f"/api/v1/incidents/attempts/{attempt_id}/cli", json={"device": "SW1", "command": "interface Fa0/5"})
    client.post(f"/api/v1/incidents/attempts/{attempt_id}/cli", json={"device": "SW1", "command": "no shutdown"})

    verify = client.post(f"/api/v1/incidents/attempts/{attempt_id}/verify", json={"device": "PC1", "command": "ping 192.168.10.1"})
    assert verify.status_code == 200, verify.text
    assert verify.json()["attempt"]["status"] == "resolved"


def test_verify_fails_before_fix_is_applied(auth_client):
    client = auth_client
    incidents = client.get("/api/v1/incidents").json()
    inc = next(i for i in incidents if i["slug"] == "inc-002-interface-down")
    start = client.post("/api/v1/incidents/attempts", json={"incident_id": inc["id"]})
    attempt_id = start.json()["id"]

    verify = client.post(f"/api/v1/incidents/attempts/{attempt_id}/verify", json={"device": "PC1", "command": "ping 192.168.10.1"})
    assert verify.status_code == 400


def test_free_tier_user_blocked_from_pro_incident(auth_client):
    client = auth_client
    incidents = client.get("/api/v1/incidents").json()
    pro_inc = next(i for i in incidents if i["is_free_tier"] is False)
    start = client.post("/api/v1/incidents/attempts", json={"incident_id": pro_inc["id"]})
    assert start.status_code == 402


def test_cannot_access_another_users_attempt(client):
    def register(email):
        resp = client.post("/api/v1/auth/register", json={"email": email, "password": "SecurePass123", "display_name": "User"})
        return resp.json()["access_token"]

    token_a = register("user-a@example.com")
    token_b = register("user-b@example.com")

    client.headers.update({"Authorization": f"Bearer {token_a}"})
    incidents = client.get("/api/v1/incidents").json()
    free_inc = next(i for i in incidents if i["is_free_tier"] is True)
    attempt = client.post("/api/v1/incidents/attempts", json={"incident_id": free_inc["id"]}).json()

    client.headers.update({"Authorization": f"Bearer {token_b}"})
    resp = client.get(f"/api/v1/incidents/attempts/{attempt['id']}")
    assert resp.status_code == 404
