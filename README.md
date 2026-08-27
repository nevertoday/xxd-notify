# xxd-notify

我做这个 Skill，起因其实很简单：让 AI 跑测试、处理一批图片，或者执行一次部署时，我不想一直守在电脑前；但我也不想让 AI 自己决定什么时候该打扰我。

所以我把这件事做成了 xxd-notify：你告诉 AI 想在什么时机收到提醒，它就通过 Bark 把进度或结果送到你的 iPhone。

## 它能怎么提醒？

你可以让它只在任务完成或失败时通知，也可以让它在每完成 20%、每个阶段、遇到异常，或者需要你做选择时通知。

比如：

> 批量处理这 500 张图片，每完成 20% 用 Bark 通知我一次；如果遇到异常也马上叫我。

AI 就会在 20%、40%、60%、80% 和 100% 这些节点汇报，而不是把每个小步骤都推到手机上。你能离开电脑，又不会失去对长任务的掌控。

再比如：

> 你先继续部署，只有遇到必须由我决定的选项时用 Bark 叫我；如果一切顺利，全部完成后再通知。

这时通知会告诉你卡在哪里、有哪些选项、推荐哪个，而不是只丢一句“请处理”。

这就是我觉得它有用的地方：Bark 负责把消息送到手机，xxd-notify 负责把“什么时候该提醒、提醒什么”这层逻辑说清楚。

## 日常怎么用？

配置好以后，不需要记命令。直接在和 Codex 或 Claude 的对话里说清楚三件事：做什么、什么时候提醒、提醒里带什么。

### 任务结束后提醒

> 帮我把这个项目的测试全部跑完。成功或失败后用 Bark 通知我，并告诉我测试结果和下一步。

### 按百分比或阶段提醒

> 把这批文件处理完，每完成 20% 用 Bark 通知我一次，告诉我进度和异常。

也可以这样说：

> 这个任务分准备、处理、检查、导出四个阶段，每完成一个阶段用 Bark 告诉我。

### 只在需要我决定时提醒

> 继续处理，只有遇到必须由我决定的事情时才用 Bark 叫我；没有需要选择的地方就全部做完后通知。

### 测试或修改提醒偏好

> 测试一下 Bark，让我确认手机能收到通知。

> 把任务提醒的声音改成 birdsong，然后发一条测试通知。

没有明确要求 Bark 时，xxd-notify 不会因为普通对话自动打扰你。

## 安装

把这个目录放进 Codex 或 Claude 使用的 skills 目录，然后让工具重新加载 Skills：

```bash
chmod +x scripts/bark_notify.sh
```

## 配置 Bark

先在 iPhone 上安装 [Bark](https://github.com/Finb/Bark)，从 App 中复制你的专属推送 URL。它通常长这样：

```text
https://api.day.app/你的BarkKey
```

把它保存到本机配置：

```bash
python3 scripts/bark_config.py set endpoint 'https://api.day.app/YOUR_BARK_KEY'
python3 scripts/bark_config.py set sound birdsong
python3 scripts/bark_config.py show
```

默认配置在 `~/.config/xxd-notify/config.json`，也可以用 `XXD_BARK_CONFIG` 指定其他位置。`show` 会自动遮蔽 Key，配置文件权限也会设为仅本人可读写。

发送一条测试：

```bash
./scripts/bark_notify.sh \
  --title '🧪 Bark 连接正常' \
  --body $'这是测试消息\n用途：xxd-notify 任务提醒'
```

只有 Bark 返回 `code: 200` 时，脚本才会报告成功。

## 给制作者的安全提醒

这个项目可以公开，但你的 Bark Key 不应该公开。它只放在本机配置里，不要写进 README、代码、Issue、截图、命令历史或 Git 历史；其他人安装后配置他们自己的 Key。

## 相关链接

- [Bark 官方项目](https://github.com/Finb/Bark)
- [Bark 发送消息接口](https://github.com/Finb/Bark#send-a-message)
- [Bark 服务端 API](https://github.com/Finb/Bark/tree/master/Server)

## License

MIT
