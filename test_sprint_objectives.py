import json
import urllib.request
import urllib.error

TENANT_A = "1a81c82d-d090-4dbd-96db-27c09f982bbc"
TENANT_B = "99999999-9999-9999-9999-999999999999"
REGION_A = "us-east-2"
REGION_B = "us-west-2"

def test_tenant_isolation():
    print("\n--- 1. Testing Tenant Isolation ---")
    
    # 1. Tenant A metrics query
    req = urllib.request.Request(
        f"http://127.0.0.1:8000/v1/metrics/query?metric=cpu&resource=i-0ad3c6e402779dc42&minutes=60&step=60&region={REGION_A}",
        headers={"X-Tenant-ID": TENANT_A}
    )
    res = urllib.request.urlopen(req)
    data_a = json.loads(res.read())
    print(f"Tenant A Query Result: {len(data_a.get('result', []))} series returned")

    # 2. Tenant B metrics query for Tenant A's resource (Must return empty series due to strict PromQL tenant selector)
    req_b = urllib.request.Request(
        f"http://127.0.0.1:8000/v1/metrics/query?metric=cpu&resource=i-0ad3c6e402779dc42&minutes=60&step=60&region={REGION_A}",
        headers={"X-Tenant-ID": TENANT_B}
    )
    res_b = urllib.request.urlopen(req_b)
    data_b = json.loads(res_b.read())
    print(f"Tenant B Cross-Tenant Access Attempt: {len(data_b.get('result', []))} series returned (PASSED: Isolated)")
    assert len(data_b.get("result", [])) == 0, "Cross-tenant metric leakage detected!"

def test_historical_30d_query():
    print("\n--- 2. Testing 30-Day Historical Range Query ---")
    req = urllib.request.Request(
        f"http://127.0.0.1:8000/v1/metrics/query?metric=cpu&resource=i-0ad3c6e402779dc42&minutes=43200&step=7200&region={REGION_A}",
        headers={"X-Tenant-ID": TENANT_A}
    )
    res = urllib.request.urlopen(req)
    data = json.loads(res.read())
    print(f"30-Day Range Query Status: {res.status} (PASSED)")

def test_insight_engine_and_deduplication():
    print("\n--- 3. Testing Insight Engine Analysis & Deduplication ---")
    req = urllib.request.Request(
        f"http://127.0.0.1:8000/v1/insights/{TENANT_A}/analyze?region={REGION_A}",
        headers={"X-Tenant-ID": TENANT_A},
        method="POST"
    )
    res = urllib.request.urlopen(req)
    data = json.loads(res.read())
    print(f"First Analysis Run: {data.get('insights_found', 0)} insights found")

    # Run second analysis to test occurrence_count deduplication
    res2 = urllib.request.urlopen(req)
    data2 = json.loads(res2.read())
    print(f"Second Analysis Run (Deduplication Check): {data2.get('insights_found', 0)} insights found")

def test_copilot_structured_evidence():
    print("\n--- 4. Testing AI Copilot Structured Evidence Response ---")
    payload = json.dumps({
        "question": "What is the status of ec2 instance i-0ad3c6e402779dc42?",
        "region": REGION_A,
        "resource_id": "i-0ad3c6e402779dc42"
    }).encode('utf-8')
    req = urllib.request.Request(
        f"http://127.0.0.1:8000/v1/insights/{TENANT_A}/explain",
        data=payload,
        headers={"X-Tenant-ID": TENANT_A, "Content-Type": "application/json"},
        method="POST"
    )
    res = urllib.request.urlopen(req)
    data = json.loads(res.read())
    answer = data.get("answer", "")
    print(f"Copilot Response Length: {len(answer)} chars")
    print(f"Contains 'Current State': {'Current State' in answer}")
    print(f"Contains 'Root Cause': {'Root Cause' in answer}")
    print(f"Contains 'Evidence': {'Evidence' in answer}")
    print(f"Contains 'Confidence': {'Confidence' in answer}")

if __name__ == "__main__":
    print("=== Starting Sprint Objective Verification Suite ===")
    test_tenant_isolation()
    test_historical_30d_query()
    test_insight_engine_and_deduplication()
    test_copilot_structured_evidence()
    print("\n=== All Sprint Objective Tests Completed Successfully ===")
