---
name: xxd-notify
description: 通过 Bark 向用户的 iPhone 发送智能任务提醒。当用户明确说“完成后通知我”“做完发 Bark”“手机提醒我”“任务结束给我消息”，或请求设置、测试、修改 Bark 通知偏好时使用。默认根据任务结果生成简洁、可决策的标题和正文，并在任务真正完成后发送；不因普通任务自动推送。
compatibility: Requires curl or Python 3 and network access. Configuration is stored locally at ~/.config/xxd-notify/config.json and is never part of the skill repository.
---

# xxd-notify：Bark 智能任务提醒

先完成用户的主任务并验证结果，再发送提醒。只在当前请求明确要求 Bark 或手机通知时发送；“记住以后”只表示保存偏好，不代表所有未来任务自动发送。

不要在回复、日志或任务产物中显示 Bark Key，也不要把本机配置复制、打包或提交到仓库。

## 模式

1. 发送模式：用户要求任务完成后提醒时，使用已保存配置发送一条终态通知。
2. 设置模式：用户要求设置、配置或修改 Bark 提醒时，先显示当前配置（隐藏 Key），再逐项询问和修改。
3. 测试模式：用户要求测试 Bark 时，发送标题“🧪 Bark 连接正常”，正文说明测试时间和主要偏好。

## 发送

确认任务已达到完成、需决策、失败或取消等真实终态后，生成一条独立可理解的通知，并调用 `scripts/bark_notify.sh`。标题约 8–20 个中文字；正文通常包括结果、产物和建议。检查返回 JSON 中的 `code` 是否为 `200`，只在成功时报告已发送。

状态符号：完成 `✅`，需决策 `⚠️`，失败 `❌`，取消 `⏹️`，测试 `🧪`。

示例：

```bash
./scripts/bark_notify.sh --title "✅ 项目介绍已生成" --body $'结果：已完成中文介绍\n产物：/absolute/path/intro.md\n建议：审阅标题和案例'
```

可用命令行参数临时覆盖 `--sound`、`--group`、`--level` 和 `--url`，不会写回配置。

## 配置

配置文件默认位置为 `~/.config/xxd-notify/config.json`，也可以通过 `XXD_BARK_CONFIG` 指定。使用配置工具查看和修改：

```bash
python3 scripts/bark_config.py show
python3 scripts/bark_config.py set sound birdsong
python3 scripts/bark_config.py set group "AI 任务"
python3 scripts/bark_config.py reset
```

推荐默认值为 `birdsong` 音效、`AI 任务` 分组、`active` 重要程度和归档消息。`bark_config.py show` 会遮蔽 endpoint 中的 Key，并将配置文件权限设为仅用户可读写。

配置缺失时，不要编造 Key；应提示用户进入设置模式。不要发送密码、令牌、完整 Key、私密对话或大段原文。
