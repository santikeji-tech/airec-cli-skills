#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feishu_push.py — 飞书自定义机器人 Webhook 发送器（纯标准库）

用法:
  feishu_push.py text  "消息内容"
  feishu_push.py post  "标题" '[[{"tag":"text","text":"第一行"}],...]'
  feishu_push.py card  "标题" "正文(markdown)" [--color green] [--webhook URL] [--secret SECRET]

配置（优先级: 命令行 > 环境变量 > ~/.airec/feishu_config.json）:
  env:  FEISHU_WEBHOOK, FEISHU_SECRET
  file: ~/.airec/feishu_config.json  {"webhook": "...", "secret": "..."}

参考实现: clarklooking/feishu-push-skill (Node.js)
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.request
import urllib.error

CONFIG_PATH = os.path.expanduser("~/.airec/feishu_config.json")


def load_config():
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f) or {}
        except Exception as e:
            print(f"⚠ 配置文件解析失败 {CONFIG_PATH}: {e}", file=sys.stderr)
    return cfg


def get_webhook(args_webhook=None):
    cfg = load_config()
    return (args_webhook or os.environ.get("FEISHU_WEBHOOK") or cfg.get("webhook") or "").strip()


def get_secret(args_secret=None):
    cfg = load_config()
    return (args_secret or os.environ.get("FEISHU_SECRET") or cfg.get("secret") or "").strip()


def gen_sign(timestamp_sec, secret):
    """飞书签名: HMAC-SHA256(timestamp\\nsecret) -> base64"""
    string_to_sign = f"{timestamp_sec}\n{secret}"
    return base64.b64encode(
        hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    ).decode("utf-8")


def send(webhook, secret, body):
    """带签名发送，返回 (ok, resp_json_or_errmsg)"""
    if not webhook:
        return False, "未配置 webhook（环境变量 FEISHU_WEBHOOK 或 ~/.airec/feishu_config.json）"
    timestamp = int(time.time())
    payload = dict(body)
    if secret:
        payload["timestamp"] = str(timestamp)
        payload["sign"] = gen_sign(timestamp, secret)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}"
    except Exception as e:
        return False, f"请求失败: {e}"
    if result.get("code") != 0:
        return False, f"飞书返回错误: {result.get('msg', result)}"
    return True, result


def build_text(text):
    return {"msg_type": "text", "content": {"text": text}}


def build_post(title, content):
    return {
        "msg_type": "post",
        "content": {"post": {"zh_cn": {"title": title, "content": content}}},
    }


def build_card(title, markdown, color="blue"):
    return {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": title}, "template": color},
            "elements": [{"tag": "markdown", "content": markdown}],
        },
    }


def main():
    p = argparse.ArgumentParser(description="飞书自定义机器人 Webhook 发送器")
    p.add_argument("type", choices=["text", "post", "card"], help="消息类型")
    p.add_argument("args", nargs="+", help="text: 内容; post: 标题+JSON; card: 标题+正文")
    p.add_argument("--color", default="blue", help="卡片标题颜色")
    p.add_argument("--webhook", default=None, help="覆盖 webhook 地址")
    p.add_argument("--secret", default=None, help="覆盖签名 secret")
    p.add_argument("--dry-run", action="store_true", help="只打印请求体不发送")
    a = p.parse_args()

    webhook = get_webhook(a.webhook)
    secret = get_secret(a.secret)

    if a.type == "text":
        body = build_text(a.args[0])
    elif a.type == "post":
        if len(a.args) < 2:
            sys.exit("post 需要: 标题 内容JSON")
        try:
            content = json.loads(a.args[1])
        except json.JSONDecodeError:
            sys.exit("post 内容不是合法 JSON")
        body = build_post(a.args[0], content)
    else:
        if len(a.args) < 2:
            sys.exit("card 需要: 标题 正文")
        body = build_card(a.args[0], a.args[1].replace("\\n", "\n"), a.color)

    if a.dry_run:
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0

    ok, result = send(webhook, secret, body)
    if not ok:
        print(f"✗ 发送失败: {result}", file=sys.stderr)
        return 1
    print("✓ 发送成功")
    return 0


if __name__ == "__main__":
    sys.exit(main())
