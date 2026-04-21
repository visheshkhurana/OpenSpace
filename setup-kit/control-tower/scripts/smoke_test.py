"""
Smoke test: spawns one L3 agent end-to-end, asserts DB rows are created.
"""
import json
import os
import sys
import urllib.request as ur

API_URL   = os.environ.get("CONTROL_TOWER_API_URL", "http://localhost:8000")
API_TOKEN = os.environ["CONTROL_TOWER_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}


def call(method: str, path: str, body: dict = None) -> dict:
    url = f"{API_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = ur.Request(url, data=data, headers=HEADERS, method=method.upper())
    with ur.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main():
    print("=== Smoke Test: Cleya Control Tower ===")
    errors = []

    # 1. Health check
    health = call("GET", "/healthz")
    assert health.get("status") in ("ok", "degraded"), f"Health check failed: {health}"
    print(f"✅ Health: {health['status']}")

    # 2. Spawn a test L3 agent
    spawn_res = call("POST", "/agents/spawn", {
        "type": "smoke-test-micro",
        "goal": "Smoke test: draft a 50-word intro email to a test lead and return it as JSON output",
        "skill_ref": "cold-email-personalizer",
        "level": 3,
        "created_by": "smoke_test",
        "metadata": {"test": True},
    })
    agent_id = spawn_res.get("agent_id")
    assert agent_id, f"Spawn failed: {spawn_res}"
    print(f"✅ Agent spawned: {agent_id}")

    task_id = spawn_res.get("bootstrap_task_id")
    assert task_id, "No bootstrap task ID"
    print(f"✅ Bootstrap task created: {task_id}")

    # 3. Check metrics endpoint
    metrics = call("GET", "/metrics")
    print(f"✅ Metrics endpoint: {len(metrics.get('metrics', []))} rows")

    # 4. List agents
    agents = call("GET", "/agents?limit=5")
    assert "agents" in agents, f"List agents failed: {agents}"
    print(f"✅ Agents listed: {len(agents['agents'])} agents")

    # 5. Meta tick
    tick = call("POST", "/meta/tick", {"cycle_number": 0, "notes": "smoke test"})
    assert "system_status" in tick, f"Meta tick failed: {tick}"
    print(f"✅ Meta tick: system_status={tick['system_status']}")

    # 6. Kill the test agent
    kill = call("POST", f"/agents/{agent_id}/kill?reason=smoke_test_cleanup")
    assert kill.get("status") == "killed", f"Kill failed: {kill}"
    print(f"✅ Agent killed")

    if errors:
        print(f"\n❌ FAILURES: {errors}")
        sys.exit(1)
    else:
        print("\n✅ ALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
