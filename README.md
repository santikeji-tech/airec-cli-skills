# airec-cli-skills · AI Agent Skills for ClawRecorder (龙虾录音卡)

[中文](#中文) | [English](#english)

---

## 中文

让任何 AI Agent 学会「听」：把录音转写变成会议纪要、待办、日程，一条命令发进企业微信 / 钉钉 / 飞书群。

**ClawRecorder（龙虾录音卡）** 是一张名片大小的 AI 录音卡：开会滑开侧面开关即录，合上即停，录音自动传手机、转写文本存云端。本仓库提供官方 AI Agent 技能（skills），让你的 Agent（Claude Code / 自建 Agent / 企业 bot）直接消费这些转写数据。

### Skills

| 技能 | 功能 |
|---|---|
| [`skills/meeting-notes`](skills/meeting-notes/) | 会议纪要生成助手：拉取录音转写，自动整理为结构化纪要（议题 / 结论 / 待办） |
| [`skills/airec-feishu-push`](skills/airec-feishu-push/) | 转录 / 纪要一条命令推送飞书群（纯文本 / 富文本 / 消息卡片） |

### 快速开始

1. **注册开发者**（手机号 + 验证码，一条命令）：
   ```bash
   airec-dev register
   ```
2. **安装技能**到你的 Agent 环境：
   ```bash
   airec-dev skill add ./skills/meeting-notes
   ```
   或手动安装：见 [skills/meeting-notes/SKILL.md](skills/meeting-notes/SKILL.md)
3. **对 Agent 说一句话**：
   > 把今天下午那个会的纪要发到企微群

Agent 自动完成：拉取转写 → 按议题整理 → 提取待办 → 发群 → 建日程。

### 输出示例

见 [examples/sample-minutes.md](examples/sample-minutes.md)

### 开放平台

- 官网：<https://www.kamooc.cn/>
- 开发者页：<https://www.kamooc.cn/developers>
- 成为开发者后：建应用 → 读数据 → 用量统计；技能可上架 [SkillHub](https://skillhub.cn/skills/org-c77c0c1n/airec-dev-v1) 分发

### License

MIT © 三体科技（stkj）

---

## English

Teach any AI Agent how to **listen**: turn recordings into meeting minutes, action items and schedules — pushed to WeCom / DingTalk / Feishu groups in one command.

**ClawRecorder** is an AI voice recorder the size of a business card: slide the switch to record, slide back to stop. Recordings auto-sync to the cloud as transcripts. This repo hosts official Agent skills that let your AI agents (Claude Code / custom agents / enterprise bots) consume those transcripts.

### Skills

| Skill | What it does |
|---|---|
| [`skills/meeting-notes`](skills/meeting-notes/) | Meeting minutes generator: fetch transcripts, structure them into topics / decisions / action items |
| [`skills/airec-feishu-push`](skills/airec-feishu-push/) | Push transcripts / minutes to Feishu groups in one command (text / rich text / message card) |

### Quick Start

```bash
airec-dev register          # register as a developer
airec-dev skill add ./skills/meeting-notes
```

Then just tell your agent: *"Send this afternoon's meeting minutes to the group."*

The agent handles the rest: fetch transcript → organize by topic → extract action items → post to group → create schedule entries.

### Developer Platform

- Website: <https://www.kamooc.cn/>
- Developers: <https://www.kamooc.cn/developers>

### License

MIT © Santi Technology (stkj)
