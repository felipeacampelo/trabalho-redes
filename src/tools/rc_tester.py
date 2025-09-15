#!/usr/bin/env python3
import argparse
import json
import re
import socket
import time
from typing import Any, Dict, List, Optional, Tuple

# ---------- Networking ----------

def send_and_recv_once(host: str, port: int, payload: str, timeout: float = 5.0) -> Tuple[float, str]:
    start = time.time()
    buf = bytearray()
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.settimeout(timeout)
        s.sendall(payload.encode("utf-8") + b"\n")  # sempre 1 linha por request
        while True:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf.extend(chunk)
            except socket.timeout:
                break
    elapsed = time.time() - start
    return elapsed, buf.decode("utf-8", errors="replace").rstrip("\r\n")

# ---------- Helpers ----------

def json_compact(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def load_cases(path: str) -> List[Dict[str, Any]]:    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    if not isinstance(data, list):
        raise ValueError("Test file must be a JSON array of cases.")
    for i, case in enumerate(data, 1):
        if not isinstance(case, dict) or "send" not in case or "expect" not in case:
            if "send" not in case and "synth" in case:
                continue
            
            raise ValueError(f"Case {i} must be an object with 'send' and 'expect'.")
    return data

def match_subset(resp: Any, subset: Any) -> bool:
    if isinstance(subset, dict):
        if not isinstance(resp, dict):
            return False
        return all(k in resp and match_subset(resp[k], v) for k, v in subset.items())
    if isinstance(subset, list):
        if not isinstance(resp, list):
            return False
        # cada item esperado deve estar contido em algum item da resposta
        return all(any(match_subset(r_item, exp_item) for r_item in resp) for exp_item in subset)
    return resp == subset

def top_level_has_keys(j: Dict[str, Any], keys: List[str]) -> bool:
    return all(k in j for k in keys)

def type_of_fields(j: Dict[str, Any], types: Dict[str, str]) -> bool:
    mapping = {"str": str, "int": int, "list": list, "dict": dict, "float": float, "number": (int, float), "bool": bool}
    for k, tname in types.items():
        if k not in j: return False
        py_t = mapping.get(tname)
        if py_t is None or not isinstance(j[k], py_t): return False
    return True

def validate_response(raw_resp: str, expect: Dict[str, Any]) -> Tuple[bool, str]:
    # regex no raw
    if "regex" in expect:
        pat = expect["regex"]
        if not re.search(pat, raw_resp):
            return False, f"regex '{pat}' not matched"
    # tenta JSON
    j = None
    try:
        j = json.loads(raw_resp)
    except Exception:
        j = None

    if "equals" in expect:
        if j is None: return False, "expected JSON equals but got non-JSON"
        if j != expect["equals"]: return False, "JSON is not equal to expected"
    if "subset" in expect:
        if j is None: return False, "expected JSON subset but got non-JSON"
        if not match_subset(j, expect["subset"]): return False, "JSON does not include expected subset"
    if "has" in expect:
        if j is None: return False, "expected JSON but got non-JSON"
        if not top_level_has_keys(j, expect["has"]): return False, f"JSON missing keys: {expect['has']}"
    if "types" in expect:
        if j is None: return False, "expected JSON but got non-JSON"
        if not type_of_fields(j, expect["types"]): return False, f"JSON type check failed for: {expect['types']}"
    if "status" in expect:
        if j is None: return False, "expected JSON status but got non-JSON"
        if j.get("status") != expect["status"]: return False, f"status={j.get('status')} != {expect['status']}"
    return True, "OK"

# ---------- Wire payload builder ----------

def build_payload(case: Dict[str, Any]) -> str:
    """
    mode:
      - "json" (default): serializa 'send' como JSON compacto
      - "raw": envia 'send' como string literal
      - "synth": gera payload sintético (ex.: muito longo) com 'synth' config
    """
    mode = case.get("mode", "json")

    if mode == "json":
        return json_compact(case["send"])
    elif mode == "raw":
        return str(case.get("send") or "")
    elif mode == "synth":
        cfg = case.get("synth", {})
        # exemplo suportado: {"pattern":"curly_a", "count":33000}
        pat = cfg.get("pattern")
        if pat == "curly_a":
            count = int(cfg.get("count", 33000))
            return "{" + ("a" * count) + "}"
        raise ValueError(f"Unknown synth pattern: {pat}")
    else:
        raise ValueError(f"Unknown mode: {mode}")

# ---------- Runner ----------

def main():
    ap = argparse.ArgumentParser(description="Rendezvous server tester (readable JSON with expected responses).")
    ap.add_argument("file", help="Path to JSON array of test cases.")
    ap.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    ap.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
    ap.add_argument("--timeout", type=float, default=5.0, help="Socket timeout (seconds)")
    ap.add_argument("--delay", type=float, default=0.0, help="Delay between cases (seconds)")
    args = ap.parse_args()

    cases = load_cases(args.file)

    total = passed = failed = 0
    for i, case in enumerate(cases, start=1):
        name = case.get("name") or f"case-{i}"
        expect = case.get("expect", {})
        payload = build_payload(case)

        total += 1
        print(f"\n[{i}] {name}\n➜ Sending: {payload if len(payload)<=200 else payload[:200]+'…'}")

        try:
            t, resp = send_and_recv_once(args.host, args.port, payload, timeout=args.timeout)
            print(f"⇦ Received ({t*1000:.1f} ms): {resp if len(resp)<=300 else resp[:300]+'…'}")
        except Exception as e:
            print(f"✖ Connection error: {e}")
            failed += 1
            if args.delay: time.sleep(args.delay)
            continue

        ok, why = validate_response(resp, expect)
        if ok:
            print("✔ PASS")
            passed += 1
        else:
            print(f"✖ FAIL: {why}")
            failed += 1

        if args.delay:
            time.sleep(args.delay)

    print("\n==== Summary ====")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")

if __name__ == "__main__":
    main()
