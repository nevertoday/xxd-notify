# xxd-notify

通过 Bark 向 iPhone 发送智能任务提醒的 Codex/Claude Skill。

Bark 是一款自托管推送工具：iPhone 安装 Bark App 后，会为你生成一个专属的推送 Key，xxd-notify 通过 Bark 的 HTTPS 接口发送消息。

相关链接：

- [Bark 官方 GitHub 项目](https://github.com/Finb/Bark)
- [Bark 官方接口说明](https://github.com/Finb/Bark#send-a-message)
- [Bark 服务端 API 文档](https://github.com/Finb/Bark/tree/master/Server)

## 特性

- 只在用户明确要求时发送任务终态提醒
- 支持完成、需决策、失败、取消和测试通知
- 支持声音、分组、重要程度、角标和跳转地址
- 配置只保存在本机，不进入 Skill 或 Git 仓库
- `show` 命令会遮蔽 Bark endpoint 中的 Key

## 安装

将本目录复制到对应的 skills 目录，并确保脚本可执行：

```bash
chmod +x scripts/bark_notify.sh
```

## 配置

首次使用前，在 iPhone 的 Bark App 中复制你的专属推送 URL。它通常形如 `https://api.day.app/你的Key`；其中最后一段就是 Bark Key。然后把完整 URL 保存到本机配置中，绝不要提交它：

```bash
python3 scripts/bark_config.py set endpoint 'https://api.day.app/YOUR_BARK_KEY'
python3 scripts/bark_config.py set sound birdsong
python3 scripts/bark_config.py show
```

默认配置路径为 `~/.config/xxd-notify/config.json`，可用 `XXD_BARK_CONFIG` 覆盖。

如果还没有 Bark：先从 [Bark 官方项目](https://github.com/Finb/Bark)进入 App 获取方式和服务端说明，再回到这里配置 endpoint。不要把真实 Key 填进 README、Issue、截图、命令示例或 Git 历史。

## 发送测试

```bash
./scripts/bark_notify.sh \
  --title '🧪 Bark 连接正常' \
  --body $'这是测试消息\n用途：xxd-notify 任务提醒'
```

脚本只有在 Bark 返回 JSON `code: 200` 时才以成功退出。

## 安全说明

本项目不包含任何真实 Bark Key、API token、密码或本机配置。Bark Key 等同于凭证：请通过本机配置文件保存，不要放入命令历史、日志、截图或公开仓库。若 Key 曾经被公开，应立即在 Bark 中重置。

## License

MIT
