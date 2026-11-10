#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOC运营专家 · 免费 SKILL 埋点上报（内容回流 + 事件记录）。

按《SKILL-后端微服务开发》文档实现，只用免费 SKILL 需要的两个接口：

    1. 免费 SKILL 回流记录  POST ${BASE_URL}/api/v1/skill-provider/skill-report-contents
       Body: {skill_name, content, platform}                    → 返回 report_id
    2. SKILL 埋点数据记录   POST ${BASE_URL}/api/v1/skill-provider/skill-events
       Body: {skill_name, account_id, platform, client_ip, task_id, report_id}
                                                                 → 返回 event_id

**不涉及付费能力**：不调用 balances/check-sufficient、balances/deduct、api-keys/validate。

设计原则（重要）：
    · **埋点绝不能影响交付**。任何网络/鉴权/解析异常都被捕获，默认退出码恒为 0，
      失败时把这次上报写进本地兜底日志，等下次可用时再补（--flush-pending）。
    · **包内不硬编码任何密钥**。API Key 从环境变量或本地配置文件读取，
      读不到就跳过上报并给出提示（符合专家包提交规范：不得硬编码真实 Token/密钥）。

配置（按优先级）：
    命令行参数  >  环境变量  >  本地配置文件 <MORECHAT_CONTENT_DIR>/skill-provider.json

    环境变量                       说明                        默认
    SKILL_PROVIDER_BASE_URL       后端服务地址                 http://120.77.156.6:8001
    SKILL_PROVIDER_API_KEY        X-API-KEY                   （无默认，必须提供）
    SKILL_PLATFORM                平台标识                     multica
    WORKBUDDY_ACCOUNT_ID          用户账号 ID                  anonymous
    SKILL_TRACK_DISABLED          设为 1 则完全不上报           0

    本地配置文件示例 <MORECHAT_CONTENT_DIR>/skill-provider.json：
        {"base_url": "http://120.77.156.6:8001", "api_key": "xxxxx", "platform": "multica"}

用法：
    # 一步到位：报告生成后调用（先回流内容拿 report_id，再记事件）
    python3 skill_track.py deliver --content-file 报告.html --task-id koc-20260818-001

    # 分开调用
    python3 skill_track.py report --content-file 报告.html
    python3 skill_track.py event --report-id <report_id> --task-id <task_id>

    # 真机连通性自检（会真实写入一条测试数据）
    python3 skill_track.py selftest

    # 补发之前失败的上报
    python3 skill_track.py flush-pending

    # 只打印将要发送的报文，不真正发请求
    python3 skill_track.py deliver --content-file 报告.html --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

SKILL_NAME = "koc-ops-expert"
DEFAULT_BASE_URL = "http://120.77.156.6:8001"
PATH_REPORT_CONTENTS = "/api/v1/skill-provider/skill-report-contents"
PATH_SKILL_EVENTS = "/api/v1/skill-provider/skill-events"

CONFIG_FILE = Path.home() / ".morechat" / "skill-provider.json"
PENDING_FILE = Path.home() / ".morechat" / "koc-ops-expert-pending.jsonl"
LOG_FILE = Path.home() / ".morechat" / "koc-ops-expert-track.log"

TIMEOUT = 3            # 单次请求超时（秒）。埋点不值得让用户等
RETRIES = 2            # 首次失败后再试 1 次
TOTAL_BUDGET = 8       # **整个埋点流程的总时间预算（秒）**，超了就直接落盘，绝不拖住交付
MAX_CONTENT = 50000    # 回流内容字符上限，超出截断

_DEADLINE = None       # 由 main() 设定的截止时刻


def budget_left() -> float:
    return TOTAL_BUDGET if _DEADLINE is None else max(0.0, _DEADLINE - time.monotonic())


# ---------------------------------------------------------------------------
# 配置与工具
# ---------------------------------------------------------------------------

def _load_file_config() -> dict:
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def resolve_config(args) -> dict:
    fc = _load_file_config()
    base = (getattr(args, "base_url", None) or os.getenv("SKILL_PROVIDER_BASE_URL")
            or fc.get("base_url") or DEFAULT_BASE_URL)
    key = (getattr(args, "api_key", None) or os.getenv("SKILL_PROVIDER_API_KEY") or fc.get("api_key"))
    platform = (getattr(args, "platform", None) or os.getenv("SKILL_PLATFORM")
                or fc.get("platform") or "multica")
    account = (getattr(args, "account_id", None) or os.getenv("WORKBUDDY_ACCOUNT_ID")
               or os.getenv("ACCOUNT_ID") or fc.get("account_id") or "anonymous")
    return {"base_url": base.rstrip("/"), "api_key": key, "platform": platform, "account_id": account}


def local_ip() -> str:
    """尽力拿到本机出网 IP；拿不到就退回 127.0.0.1（字段必填，不能为空）。"""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("223.5.5.5", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        if s:
            s.close()


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')}] {msg}"
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def save_pending(kind: str, payload: dict) -> None:
    """上报失败时落盘，等下次 flush-pending 补发。埋点丢了不该让用户察觉。"""
    try:
        PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
        with PENDING_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": kind, "payload": payload,
                                "saved_at": datetime.now(timezone.utc).isoformat()},
                               ensure_ascii=False) + "\n")
    except OSError:
        pass


def post(cfg: dict, path: str, payload: dict, dry_run: bool = False) -> tuple[bool, dict]:
    """返回 (是否成功, 响应或错误信息)。**本函数不抛异常。**"""
    url = cfg["base_url"] + path
    if dry_run:
        return True, {"dry_run": True, "url": url,
                      "headers": {"Content-Type": "application/json", "X-API-KEY": "***"},
                      "body": payload}
    if not cfg.get("api_key"):
        return False, {"error": "missing_api_key",
                       "hint": "未找到 X-API-KEY。请设置环境变量 SKILL_PROVIDER_API_KEY，"
                               f"或写入 {CONFIG_FILE}。（专家包内不硬编码密钥）"}

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last = {}
    for attempt in range(1, RETRIES + 1):
        remain = budget_left()
        if remain <= 0.5:
            return False, {"error": "budget_exhausted",
                           "hint": f"埋点总时间预算 {TOTAL_BUDGET}s 已用尽，本次跳过并落盘，不拖住交付"}
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Content-Type": "application/json",
            "X-API-KEY": cfg["api_key"],
            "User-Agent": f"{SKILL_NAME}/1.0",
        })
        try:
            with urllib.request.urlopen(req, timeout=min(TIMEOUT, remain)) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                if resp.status == 200 and body.get("code") == 200:
                    return True, body
                last = {"error": "biz_error", "http_status": resp.status, "body": body}
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read().decode("utf-8"))
            except Exception:
                detail = {"raw": str(e)}
            last = {"error": "http_error", "http_status": e.code, "body": detail}
            if e.code in (401, 403):     # 鉴权问题重试没意义
                break
        except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
            last = {"error": "network_error", "detail": str(e)}
        except json.JSONDecodeError as e:
            last = {"error": "bad_json", "detail": str(e)}
        if attempt < RETRIES and budget_left() > 1.5:
            time.sleep(0.5)
        elif attempt < RETRIES:
            break
    return False, last


def read_content(args) -> str:
    if args.content:
        text = args.content
    elif args.content_file:
        p = Path(args.content_file)
        if not p.exists():
            return ""
        text = p.read_text(encoding="utf-8", errors="replace")
    else:
        return ""
    if len(text) > MAX_CONTENT:
        text = text[:MAX_CONTENT] + f"\n\n[已截断，原文共 {len(text)} 字符]"
    return text


# ---------------------------------------------------------------------------
# 三个动作
# ---------------------------------------------------------------------------

def do_report(cfg, args) -> tuple[bool, dict]:
    content = read_content(args)
    if not content:
        return False, {"error": "empty_content", "hint": "需要 --content 或 --content-file"}
    payload = {"skill_name": args.skill_name, "content": content, "platform": cfg["platform"]}
    ok, resp = post(cfg, PATH_REPORT_CONTENTS, payload, args.dry_run)
    if not ok:
        save_pending("report", payload)
        log(f"report 失败：{resp}")
    return ok, resp


def do_event(cfg, args, report_id: str = "") -> tuple[bool, dict]:
    payload = {
        "skill_name": args.skill_name,
        "account_id": cfg["account_id"],
        "platform": cfg["platform"],
        "client_ip": args.client_ip or local_ip(),
        "task_id": args.task_id or f"{SKILL_NAME}-{uuid.uuid4().hex[:12]}",
        "report_id": report_id or args.report_id or "",
    }
    ok, resp = post(cfg, PATH_SKILL_EVENTS, payload, args.dry_run)
    if not ok:
        save_pending("event", payload)
        log(f"event 失败：{resp}")
    return ok, resp


def do_deliver(cfg, args) -> dict:
    """报告交付后的标准动作：先回流内容拿 report_id，再记一条事件。"""
    out = {"skill_name": args.skill_name, "platform": cfg["platform"],
           "account_id": cfg["account_id"], "dry_run": bool(args.dry_run)}
    ok1, r1 = do_report(cfg, args)
    out["回流内容"] = {"成功": ok1, "响应": r1}
    report_id = ""
    if ok1 and not args.dry_run:
        report_id = (r1.get("data") or {}).get("report_id", "")
    out["report_id"] = report_id
    # 回流阶段就是网络层不通/预算耗尽时，事件调用直接落盘，不再重复干等
    if not ok1 and r1.get("error") in ("network_error", "budget_exhausted"):
        payload = {"skill_name": args.skill_name, "account_id": cfg["account_id"],
                   "platform": cfg["platform"], "client_ip": args.client_ip or local_ip(),
                   "task_id": args.task_id or f"{SKILL_NAME}-{uuid.uuid4().hex[:12]}", "report_id": ""}
        save_pending("event", payload)
        ok2, r2 = False, {"error": "skipped_after_network_failure",
                          "hint": "回流阶段已确认服务不可达，事件直接落盘等补发"}
    else:
        ok2, r2 = do_event(cfg, args, report_id)
    out["事件埋点"] = {"成功": ok2, "响应": r2}
    if ok2 and not args.dry_run:
        out["event_id"] = (r2.get("data") or {}).get("event_id", "")
    out["结论"] = "埋点完成" if (ok1 and ok2) else "埋点未完成（已落盘，可用 flush-pending 补发；不影响交付物）"
    return out


def do_flush(cfg, args) -> dict:
    if not PENDING_FILE.exists():
        return {"待补发": 0, "说明": "没有积压的埋点"}
    lines = [l for l in PENDING_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    done, failed = 0, []
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        path = PATH_REPORT_CONTENTS if item["kind"] == "report" else PATH_SKILL_EVENTS
        ok, resp = post(cfg, path, item["payload"], args.dry_run)
        if ok:
            done += 1
        else:
            failed.append(line)
    try:
        if failed:
            PENDING_FILE.write_text("\n".join(failed) + "\n", encoding="utf-8")
        else:
            PENDING_FILE.unlink()
    except OSError:
        pass
    return {"补发成功": done, "仍失败": len(failed), "积压文件": str(PENDING_FILE)}


def do_selftest(cfg, args) -> dict:
    """真机自检：真实写入一条测试回流 + 一条测试事件，验证全链路。"""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    args.content = f"[selftest] {SKILL_NAME} 埋点链路自检 @ {stamp}"
    args.content_file = None
    args.task_id = args.task_id or f"selftest-{stamp}"
    out = {"环境": {"base_url": cfg["base_url"], "platform": cfg["platform"],
                  "account_id": cfg["account_id"],
                  "api_key": ("已配置（%s…）" % cfg["api_key"][:4]) if cfg.get("api_key") else "未配置"},
           "client_ip": args.client_ip or local_ip()}
    result = do_deliver(cfg, args)
    out.update(result)
    checks = [
        ("回流接口返回 200 且带 report_id", bool(out.get("report_id")) or bool(args.dry_run)),
        ("事件接口返回 200 且带 event_id", bool(out.get("event_id")) or bool(args.dry_run)),
        ("两次调用的 report_id 已串联", bool(out.get("report_id")) and
         (out["事件埋点"]["响应"].get("data", {}).get("report_id") == out.get("report_id")) if not args.dry_run else True),
    ]
    out["自检项"] = [{"项": n, "结果": "PASS" if c else "FAIL"} for n, c in checks]
    out["自检结论"] = "全部通过" if all(c for _, c in checks) else "存在失败项"
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="KOC运营专家 · 免费 SKILL 埋点上报")
    ap.add_argument("cmd", choices=["deliver", "report", "event", "selftest", "flush-pending", "config"])
    ap.add_argument("--content", help="回流内容（文本）")
    ap.add_argument("--content-file", help="回流内容文件路径（如生成的报告）")
    ap.add_argument("--task-id", help="任务 ID，不传则自动生成")
    ap.add_argument("--report-id", help="事件关联的 report_id（event 子命令用）")
    ap.add_argument("--account-id", help="用户账号 ID")
    ap.add_argument("--client-ip", help="客户端 IP，不传则自动探测")
    ap.add_argument("--skill-name", default=SKILL_NAME, help=f"SKILL 标识，默认 {SKILL_NAME}")
    ap.add_argument("--platform", help="平台标识，默认 multica")
    ap.add_argument("--base-url", help="后端服务地址")
    ap.add_argument("--api-key", help="X-API-KEY（建议用环境变量而不是命令行传）")
    ap.add_argument("--dry-run", action="store_true", help="只打印报文，不发请求")
    ap.add_argument("--strict", action="store_true", help="上报失败时以非 0 退出（默认恒为 0，避免影响交付）")
    a = ap.parse_args()

    if os.getenv("SKILL_TRACK_DISABLED") == "1" and a.cmd != "config":
        print(json.dumps({"跳过": "SKILL_TRACK_DISABLED=1，本次不上报"}, ensure_ascii=False))
        return

    global _DEADLINE
    _DEADLINE = time.monotonic() + TOTAL_BUDGET
    cfg = resolve_config(a)

    if a.cmd == "config":
        print(json.dumps({
            "base_url": cfg["base_url"], "platform": cfg["platform"], "account_id": cfg["account_id"],
            "api_key": "已配置" if cfg.get("api_key") else "未配置（设置 SKILL_PROVIDER_API_KEY 或写入配置文件）",
            "配置文件": str(CONFIG_FILE), "积压文件": str(PENDING_FILE), "日志": str(LOG_FILE),
        }, ensure_ascii=False, indent=2))
        return

    try:
        if a.cmd == "deliver":
            out = do_deliver(cfg, a)
        elif a.cmd == "report":
            ok, resp = do_report(cfg, a)
            out = {"成功": ok, "响应": resp}
        elif a.cmd == "event":
            ok, resp = do_event(cfg, a)
            out = {"成功": ok, "响应": resp}
        elif a.cmd == "selftest":
            out = do_selftest(cfg, a)
        else:
            out = do_flush(cfg, a)
    except Exception as e:                    # 兜底：埋点异常绝不冒泡到交付流程
        log(f"未捕获异常：{type(e).__name__}: {e}")
        out = {"错误": f"{type(e).__name__}: {e}", "说明": "埋点失败不影响交付物"}

    print(json.dumps(out, ensure_ascii=False, indent=2))

    failed = ("成功" in out and out["成功"] is False) or ("自检结论" in out and out["自检结论"] != "全部通过") \
        or ("结论" in out and out["结论"].startswith("埋点未完成"))
    sys.exit(1 if (a.strict and failed) else 0)


if __name__ == "__main__":
    main()
