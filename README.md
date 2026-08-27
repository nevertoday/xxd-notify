# xxd-notify

让 Codex 和 Claude 在任务真正结束时，主动把结果提醒到你的 iPhone。

## 它解决什么问题？

当 AI 正在跑测试、构建项目、处理大量文件或执行部署时，你不必一直盯着对话窗口。xxd-notify 把“任务完成后告诉我”变成一个可复用的通知能力：AI 根据任务结果，在完成、失败、需要你决策或取消时发送一条清楚的 Bark 提醒。

### 当你不想守着任务进度时

你让 AI 跑一整套测试，预计要十几分钟。与其盯着终端里不断滚动的日志，不如起身去泡杯咖啡、开个会，或者直接合上电脑。测试结束后，手机收到一条提醒，你再回来处理结果——等待时间真正变成了可用时间。

### 当任务失败比任务完成更值得知道时

部署进行到一半，某个环境变量缺失，流程停在服务器上。你不需要反复刷新窗口，也不会把“应该已经完成”误当成“已经完成”。xxd-notify 会把失败状态明确送到手机，让你及时回来修复，而不是几个小时后才发现任务根本没有结束。

### 当 AI 需要你做选择，但不该替你做决定时

AI 已经把部署准备好，却发现生产域名有两个可选项。它不会擅自继续，也不会只发一句模糊的“请查看”。提醒里会告诉你卡在哪里、有哪些选项以及推荐哪一个；你只要做出选择，任务就能继续往下走。

### 当你只想被结果打扰时

长任务运行期间，手机不会每隔一分钟收到“正在处理”的噪音。只有在任务完成、失败、需要决策或取消时，才发一条有上下文的消息：结果是什么、产物在哪里、接下来该做什么。你看到通知时，不必重新翻完整段对话才能判断情况。

### 当你担心把 Bark Key 一起开源时

你可以把这个 Skill 放进公开仓库，让别人复用它的提醒逻辑，但自己的 Bark Key 始终留在本机配置文件里。仓库里只有代码、说明和示例，不包含你的个人 endpoint 或任何凭证。

一句话使用它：

> “帮我跑完整套测试，完成后用 Bark 通知我。”

## 它和直接调用 Bark 有什么区别？

直接调用 Bark 只能解决“消息发出去”。xxd-notify 额外提供了任务状态判断、通知文案规范、配置管理、Key 遮蔽和失败处理，因此适合作为 Codex/Claude 的统一提醒层，而不是某一个脚本里的临时 API 调用。

## Bark 是什么？

Bark 是一款自托管推送工具：iPhone 安装 Bark App 后，会为你生成一个专属的推送 Key，xxd-notify 通过 Bark 的 HTTPS 接口发送消息。

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
