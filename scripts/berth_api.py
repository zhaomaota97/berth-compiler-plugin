#!/usr/bin/env python3
"""Claude Compiler client for Berth contract, probes, clean publishing, and feedback."""

from __future__ import annotations
import argparse, fnmatch, io, json, os, pathlib, re, subprocess, tarfile, time
import urllib.error, urllib.parse, urllib.request

PLATFORMS = {
    "local": {"name": "本地服", "url": "http://127.0.0.1:8600"},
    "competition": {"name": "比赛服", "url": "http://61.29.254.146"},
}
IGNORES = {"node_modules", ".output", ".eve", ".workflow-data", ".git", "__pycache__", ".DS_Store"}
PATTERNS = {"*.log", "*.tmp", "*.swp", ".berth-*.log"}
PLUGIN_VERSION = "2.4.0"
LATEST_MANIFEST_URL = "https://raw.githubusercontent.com/zhaomaota97/berth-compiler-plugin/master/plugin.json"


def request(platform, path, *, method="GET", data=None, auth=False, content_type="application/json"):
    headers = {"Accept": "application/json"}
    if data is not None: headers["Content-Type"] = content_type
    if auth:
        token = os.environ.get("BERTH_TOKEN", "").strip()
        if not token.startswith("bt_"): raise SystemExit("BERTH_TOKEN must be a bt_ developer token")
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(PLATFORMS[platform]["url"] + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            body = response.read(); return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Berth API {exc.code}: {exc.read().decode('utf-8', 'replace')}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Cannot reach {PLATFORMS[platform]['url']}: {exc.reason}") from exc


def auth_request(args, path, *, method="GET", body=None):
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    return request(args.platform, path, method=method, data=data, auth=True)


def rules(package):
    names, patterns = set(IGNORES), set(PATTERNS)
    ignore = package / ".berthignore"
    if ignore.is_file():
        for raw in ignore.read_text(encoding="utf-8").splitlines():
            item = raw.strip().strip("/")
            if item and not item.startswith("#"):
                (patterns if any(c in item for c in "*?[") else names).add(item)
    return names, patterns


def package_payload(package):
    names, patterns = rules(package); selected = []
    for root, dirs, files in os.walk(package):
        dirs[:] = sorted(d for d in dirs if d not in names and not any(fnmatch.fnmatch(d, p) for p in patterns))
        for name in sorted(files):
            if name in names or any(fnmatch.fnmatch(name, p) for p in patterns): continue
            path = pathlib.Path(root) / name; selected.append((path, path.relative_to(package)))
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for path, rel in selected: archive.add(path, arcname=f"{package.name}/{rel.as_posix()}", recursive=False)
    payload = buffer.getvalue()
    largest = sorted(((p.stat().st_size, r.as_posix()) for p, r in selected), reverse=True)[:5]
    return payload, {"files": len(selected), "source_bytes": sum(p.stat().st_size for p, _ in selected),
                     "archive_bytes": len(payload), "largest": largest}


def models(args):
    discovered = request(args.platform, "/v1/models").get("data", [])
    available, unavailable = [], []
    for item in discovered:
        model_id = str(item.get("id", "")).strip()
        if not model_id: continue
        try:
            result = auth_request(args, "/v1/dev/model-probe/" + urllib.parse.quote(model_id, safe=""), method="POST")
            if result.get("ok"):
                available.append({**item, "availability": "available",
                                  "probe": {"elapsed_seconds": result.get("elapsed_seconds")}})
            else:
                unavailable.append({"id": model_id, "error": result.get("error", "probe failed")})
        except SystemExit as exc:
            unavailable.append({"id": model_id, "error": str(exc)[:500]})
    print(json.dumps({"object": "list", "data": available,
                      "filtered_unavailable": unavailable}, ensure_ascii=False, indent=2), flush=True)


def check_update(args):
    try:
        with urllib.request.urlopen(LATEST_MANIFEST_URL, timeout=15) as response:
            latest = str(json.loads(response.read()).get("version", "")).split("+", 1)[0]
    except Exception as exc:
        print(json.dumps({"checked": False, "current": PLUGIN_VERSION,
                          "warning": f"无法检查 Plugin 更新: {exc}"}, ensure_ascii=False), flush=True)
        return
    current = PLUGIN_VERSION.split("+", 1)[0]
    def version_key(value):
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)", value)
        return tuple(map(int, match.groups())) if match else (0, 0, 0)
    outdated = version_key(latest) > version_key(current)
    result = {"checked": True, "current": current, "latest": latest,
              "outdated": outdated, "updated": False}
    if outdated and args.auto:
        completed = subprocess.run(
            ["claude", "plugin", "install", "berth-compiler@berth-platform"],
            text=True, capture_output=True)
        result["updated"] = completed.returncode == 0
        if completed.returncode != 0: result["error"] = (completed.stderr or completed.stdout)[-1000:]
        else: result["restart_required"] = True
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    if outdated and args.auto and not result["updated"]: raise SystemExit(1)


def publish(args, asynchronous):
    package = pathlib.Path(args.package).resolve()
    if not (package / "berth.json").is_file(): raise SystemExit(f"Missing berth.json in {package}")
    contract = auth_request(args, "/v1/dev/compiler-contract")
    payload, stats = package_payload(package); limit = int(contract["package"]["upload_max_mb"])
    print(json.dumps({"archive": stats, "limit_mb": limit}, ensure_ascii=False), flush=True)
    if len(payload) > limit * 1024 * 1024: raise SystemExit(f"Clean archive exceeds {limit}MB")
    endpoint = "/v1/dev/publish-async" if asynchronous else "/v1/dev/publish"
    endpoint += "?" + urllib.parse.urlencode({"visibility": args.visibility})
    result = request(args.platform, endpoint, method="POST", data=payload, auth=True, content_type="application/gzip")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    job_id = result.get("job_id") if isinstance(result, dict) else None
    if not asynchronous or not job_id or args.no_wait: return
    deadline = time.monotonic() + args.timeout; previous = None
    while time.monotonic() < deadline:
        job = auth_request(args, f"/v1/dev/publish-jobs/{job_id}")
        signature = (job.get("status"), job.get("updated_at"), job.get("error"))
        if signature != previous: print(json.dumps(job, ensure_ascii=False), flush=True); previous = signature
        if job.get("status") in {"succeeded", "failed", "cancelled", "timed_out"}:
            if job.get("status") != "succeeded": raise SystemExit(1)
            return
        time.sleep(args.poll_interval)
    raise SystemExit(f"Publish job {job_id} did not finish within {args.timeout}s")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--platform", choices=PLATFORMS, default="competition")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("platforms", "verify-token", "models", "contract"): sub.add_parser(name)
    update = sub.add_parser("check-update"); update.add_argument("--auto", action="store_true")
    probe = sub.add_parser("model-probe"); probe.add_argument("model")
    feedback = sub.add_parser("feedback"); feedback.add_argument("markdown"); feedback.add_argument("--plugin-version", default="")
    feedback.add_argument("--operation", choices=("create", "reconstruct"), required=True)
    feedback.add_argument("--agent-id", action="append", default=[]); feedback.add_argument("--publish-job", default="")
    for name in ("publish", "publish-async"):
        p = sub.add_parser(name); p.add_argument("package"); p.add_argument("--visibility", choices=("private", "public"), required=True)
        if name == "publish-async":
            p.add_argument("--no-wait", action="store_true"); p.add_argument("--timeout", type=float, default=1800)
            p.add_argument("--poll-interval", type=float, default=2)
    args = parser.parse_args()
    if args.command == "platforms": print(json.dumps(PLATFORMS, ensure_ascii=False, indent=2))
    elif args.command == "verify-token":
        me = auth_request(args, "/v1/dev/me"); print(json.dumps({"valid": True, "developer_id": me.get("developer_id")}, ensure_ascii=False), flush=True)
    elif args.command == "models": models(args)
    elif args.command == "check-update": check_update(args)
    elif args.command == "contract": print(json.dumps(auth_request(args, "/v1/dev/compiler-contract"), ensure_ascii=False, indent=2))
    elif args.command == "model-probe":
        print(json.dumps(auth_request(args, "/v1/dev/model-probe/" + urllib.parse.quote(args.model, safe=""), method="POST"), ensure_ascii=False, indent=2))
    elif args.command == "feedback":
        body = {"plugin": "claude-code", "plugin_version": args.plugin_version, "operation": args.operation,
                "agent_ids": args.agent_id, "publish_job_id": args.publish_job,
                "markdown": pathlib.Path(args.markdown).read_text(encoding="utf-8")}
        print(json.dumps(auth_request(args, "/v1/dev/feedback", method="POST", body=body), ensure_ascii=False, indent=2))
    elif args.command == "publish": publish(args, False)
    else: publish(args, True)


if __name__ == "__main__": main()
