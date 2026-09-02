#!/usr/bin/env python3
"""meeting-notes 技能运行时脚本 —— 用 API Key 从龙虾录音卡开放平台拉取转录并生成会议纪要

衔接 airec-dev 开放平台数据面：
    GET /api/v1/transcriptions?limit=&offset=   (header: X-Airec-Api-Key)
API Key 来源（按优先级）：
    1. --key 参数
    2. 环境变量 AIREC_API_KEY
    3. ~/.airec/dev_keys.json（dev CLI 提交技能时保存，取第一条）

用法示例：
    python3 meeting_notes.py                      # 最近 20 条，输出 markdown 纪要
    python3 meeting_notes.py --limit 100          # 拉 100 条
    python3 meeting_notes.py --since 2026-08-01   # 按日期过滤
    python3 meeting_notes.py --keyword 会议       # 关键词过滤
    python3 meeting_notes.py --format txt         # 纯文本（适合直接喂给 LLM）
    python3 meeting_notes.py --json               # 原始 JSON

只依赖 Python 标准库（urllib），无第三方包，满足平台依赖白名单。
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

DEFAULT_API = "http://111.230.182.6:8004"
KEYS_FILE = os.path.expanduser("~/.airec/dev_keys.json")
# 本技能名：从 dev_keys.json 中按 skill_name 精确匹配取 Key（一把 Key 只绑定一个技能）
SKILL_NAME = "meeting-notes"


def load_api_key(cli_key: str) -> str:
    if cli_key:
        return cli_key
    env = os.environ.get("AIREC_API_KEY")
    if env:
        return env
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE) as f:
                entries = json.load(f)
            if entries and isinstance(entries, list):
                # 按技能名精确匹配（同技能多次提交会生成多把 Key，取最新一条）
                mine = [e for e in entries if e.get("skill_name") == SKILL_NAME]
                if mine:
                    key = mine[-1].get("api_key")
                    if key:
                        return key
        except Exception:
            pass
    sys.exit(f"未找到 {SKILL_NAME} 的 API Key：请用 --key 传入，或设置 AIREC_API_KEY，或先运行 airec-dev skill add 提交本技能。\n参考文件：{KEYS_FILE}")


def fetch_transcriptions(api_key: str, api: str, limit: int, offset: int) -> dict:
    q = urllib.parse.urlencode({"limit": limit, "offset": offset})
    url = f"{api}/api/v1/transcriptions?{q}"
    req = urllib.request.Request(url, headers={"X-Airec-Api-Key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        sys.exit(f"API 请求失败 HTTP {e.code}: {body}")
    except Exception as e:
        sys.exit(f"API 请求异常: {e}")


def fetch_all(api_key: str, api: str, max_items: int) -> list[dict]:
    """分页拉取全部转录（每页 100，直到 total 或 max_items）"""
    items: list[dict] = []
    offset = 0
    page_size = 100
    while True:
        data = fetch_transcriptions(api_key, api, page_size, offset)
        page = data.get("items", [])
        items.extend(page)
        total = data.get("total", 0)
        offset += len(page)
        if not page or offset >= total or (max_items and len(items) >= max_items):
            break
    if max_items:
        items = items[:max_items]
    return items


def filter_items(items: list[dict], keyword: str = "", since: str = "") -> list[dict]:
    result = items
    if keyword:
        kw = keyword.lower()
        result = [it for it in result if kw in (it.get("text_preview") or "").lower()]
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=timezone.utc)
            result = [it for it in result
                      if it.get("created_at") and datetime.fromisoformat(it["created_at"].replace("Z", "+00:00")) >= since_dt]
        except ValueError:
            sys.exit(f"--since 格式错误: {since}（示例 2026-08-01 或 2026-08-01T00:00:00Z）")
    return result


def to_markdown(items: list[dict]) -> str:
    if not items:
        return "# 会议纪要\n\n（无匹配的转录记录）\n"
    lines = ["# 会议纪要\n"]
    for it in items:
        ts = (it.get("created_at") or "")[:19].replace("T", " ")
        dur = it.get("duration_seconds", 0)
        lines.append(f"## {it.get('id')}  ·  {ts}  ·  {it.get('device_name', '')}  ·  {dur}s")
        preview = it.get("text_preview") or "（空转录）"
        lines.append(f"> {preview}")
        lines.append("")
        lines.append("- 主题：")
        lines.append("- 结论：")
        lines.append("- 待办：")
        lines.append("")
    lines.append("---")
    lines.append("_由 meeting-notes 技能生成（转录预览为前 200 字，完整文本请用 airec CLI 或 App 查看）_")
    return "\n".join(lines)


def to_txt(items: list[dict]) -> str:
    if not items:
        return "（无匹配的转录记录）\n"
    lines = []
    for it in items:
        ts = (it.get("created_at") or "")[:19].replace("T", " ")
        dur = it.get("duration_seconds", 0)
        lines.append(f"## {ts} | {it.get('device_name', '')} | {dur}s")
        lines.append(it.get("text_preview") or "（空转录）")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="meeting-notes：拉取录音转录生成会议纪要")
    p.add_argument("--key", help="API Key（默认读 AIREC_API_KEY 或 ~/.airec/dev_keys.json）")
    p.add_argument("--api", default=DEFAULT_API, help=f"API 地址（默认 {DEFAULT_API}）")
    p.add_argument("--limit", type=int, default=20, help="最多拉取条数（默认 20）")
    p.add_argument("--keyword", default="", help="按关键词过滤转录内容")
    p.add_argument("--since", default="", help="起始时间，如 2026-08-01 或 2026-08-01T00:00:00Z")
    p.add_argument("--days", type=int, default=0, help="最近 N 天（等价 --since 今天-N 天）")
    p.add_argument("--format", choices=["markdown", "txt"], default="markdown", help="输出格式")
    p.add_argument("--json", action="store_true", help="输出原始 JSON（忽略 --format）")
    args = p.parse_args()

    if args.days:
        since = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%dT00:00:00Z")
        args.since = since

    api_key = load_api_key(args.key)
    items = fetch_all(api_key, args.api, args.limit)
    items = filter_items(items, keyword=args.keyword, since=args.since)

    if args.json:
        print(json.dumps({"success": True, "total": len(items), "items": items}, ensure_ascii=False, indent=2))
        return 0
    print(to_markdown(items) if args.format == "markdown" else to_txt(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
