#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
airec_to_feishu.py — 拉 ClawRecorder 录音转录 → 推送到飞书群（纯标准库）

用法:
  airec_to_feishu.py                     # 拉最近 3 条转录，文本消息推送
  airec_to_feishu.py --limit 10          # 最近 10 条
  airec_to_feishu.py --keyword 会议      # 只推预览含关键词的
  airec_to_feishu.py --card              # 消息卡片格式
  airec_to_feishu.py --dry-run           # 只打印不真发（联调用）

配置:
  飞书 webhook:  env FEISHU_WEBHOOK / ~/.airec/feishu_config.json 的 webhook
  签名 secret:   env FEISHU_SECRET  / 配置文件 secret（未开签名可留空）
  数据面地址:    env AIREC_BASE_URL / 配置文件 base_url
                 （GET {base_url}/api/v1/transcriptions）
  API Key:       ~/.airec/dev_keys.json 按 skill_name 匹配，优先 owner=user
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from feishu_push import get_webhook, get_secret, send, build_text, build_card

CONFIG_PATH = os.path.expanduser("~/.airec/feishu_config.json")
KEYS_PATH = os.path.expanduser("~/.airec/dev_keys.json")
DEFAULT_BASE_URL = os.environ.get("AIREC_BASE_URL", "http://111.230.182.6:8004")
DEFAULT_SKILL = "meeting-notes"


def load_config():
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f) or {}
        except Exception:
            pass
    return cfg


def get_base_url():
    return os.environ.get("AIREC_BASE_URL") or load_config().get("base_url") or DEFAULT_BASE_URL


def find_api_key(skill_name=None):
    """按 skill_name 精确匹配，优先 owner=user，取最新一条。返回 (skill_name, api_key) 或 None"""
    if not os.path.exists(KEYS_PATH):
        return None
    try:
        with open(KEYS_PATH, encoding="utf-8") as f:
            keys = json.load(f)
    except Exception:
        return None
    if not isinstance(keys, list):
        return None
    skill_name = skill_name or os.environ.get("AIREC_SKILL") or DEFAULT_SKILL
    matches = [k for k in keys if k.get("skill_name") == skill_name]
    if not matches:
        return None
    matches.sort(key=lambda k: k.get("created_at", ""), reverse=True)
    for k in matches:
        if k.get("owner") == "user":
            return k["skill_name"], k["api_key"]
    last = matches[0]
    return last["skill_name"], last["api_key"]


def fetch_transcriptions(base_url, api_key, limit=20, offset=0):
    url = f"{base_url.rstrip('/')}/api/v1/transcriptions?limit={limit}&offset={offset}"
    req = urllib.request.Request(url, headers={"X-Airec-Api-Key": api_key})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    p = argparse.ArgumentParser(description="拉 ClawRecorder 转录推送到飞书群")
    p.add_argument("--limit", type=int, default=3, help="拉最近 N 条（默认 3）")
    p.add_argument("--keyword", default=None, help="只推预览/标题含关键词的转录")
    p.add_argument("--skill", default=None, help="dev_keys.json 里的 skill_name（默认 meeting-notes）")
    p.add_argument("--card", action="store_true", help="用消息卡片格式推送")
    p.add_argument("--dry-run", action="store_true", help="只打印内容不发送")
    a = p.parse_args()

    base_url = get_base_url()
    webhook = get_webhook()
    secret = get_secret()

    if a.dry_run:
        print(f"[dry-run] base_url={base_url} webhook={webhook or '(未配置)'} "
              f"secret={'已配置' if secret else '未配置'}")

    found = find_api_key(a.skill)
    if not found:
        sys.exit("✗ 在 ~/.airec/dev_keys.json 没找到可用 Key。\n"
                 "  先 airec login + airec install 装技能（详见 airec-dev 技能），\n"
                 "  或用 --skill 指定 dev_keys.json 里已存在的 skill_name。")
    skill_name, api_key = found
    if a.dry_run:
        print(f"[dry-run] 使用 Key: skill={skill_name} tail={api_key[-4:]}")
    else:
        print(f"使用 Key: skill={skill_name}")

    # 拉转录（分页拉 limit 条）
    items, offset = [], 0
    try:
        while len(items) < a.limit:
            page = fetch_transcriptions(base_url, api_key, limit=min(100, a.limit), offset=offset)
            page_items = page.get("items", [])
            items.extend(page_items)
            offset += len(page_items)
            if offset >= page.get("total", 0) or not page_items:
                break
        items = items[: a.limit]
    except urllib.error.HTTPError as e:
        sys.exit(f"✗ 拉转录失败 HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}")
    except Exception as e:
        sys.exit(f"✗ 拉转录失败: {e}")

    if not items:
        sys.exit("没有拉到转录（检查 base_url / Key 归属）")

    # 过滤关键词
    if a.keyword:
        items = [i for i in items if a.keyword in (i.get("text_preview", "") or "")]
        if not items:
            sys.exit(f"没有预览含「{a.keyword}」的转录")

    if a.card:
        lines = []
        for i in items:
            t = (i.get("text_preview", "") or "").replace("\n", " ").strip()
            lines.append(f"**{i.get('device_name','?')}** · {i.get('created_at','')[:16]}")
            lines.append(f"{t[:120]}{'…' if len(t) > 120 else ''}")
            lines.append("---")
        body = build_card("📝 ClawRecorder 转录", "\n".join(lines), "blue")
    else:
        parts = []
        for i in items:
            t = (i.get("text_preview", "") or "").strip()
            parts.append(f"[{i.get('created_at','')[:16]} {i.get('device_name','?')}]\n{t}")
        body = build_text("📝 ClawRecorder 转录\n\n" + "\n\n".join(parts))

    if a.dry_run:
        print("\n--- 将推送的内容 ---")
        if "card" in body:
            print(body["card"]["elements"][0]["content"])
        else:
            print(body["content"])
        return 0

    ok, result = send(webhook, secret, body)
    if not ok:
        print(f"✗ 推送失败: {result}", file=sys.stderr)
        return 1
    print(f"✓ 已推送 {len(items)} 条转录到飞书群")
    return 0


if __name__ == "__main__":
    sys.exit(main())
