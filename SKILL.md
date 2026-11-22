---
name: xxd-notify
description: 通过 Bark 把 AI 任务里需要用户的时刻推到 iPhone：要用户拍板（选方案、花钱、对真实用户发消息、删数据、登录授权）、失败或停下、做完了，以及用户点名的进度节点。用户说“做完通知我”“做完发 Bark”“手机提醒我”“需要我确认/选择时 Bark 我”“loop 里要我拍板就叫我”“这个命令跑完推一下”“盯着这个进程/日志，卡住就提醒”，或要设置、测试、修改 Bark 时使用。用户说“Codex/Claude/Antigravity/Grok 额度重置了提醒我”“盯着额度重置”“不用再提醒重置了”时，设置或关掉 AI 额度重置提醒。用户没要求时不推送。
compatibility: Python 3.8+（只用标准库）和能连到 Bark 服务器的网络。配置在本机 ~/.config/xxd-notify/config.json，不进仓库。
---

# xxd-notify：只在需要你的时候，手机响一下

Bark 负责把消息送到 iPhone；这个 Skill 负责什么时候该打扰、写什么、怎么确保送到。

所有命令都在 `scripts/xxd_notify.py`（下文简写为 `notify`）。旧入口 `scripts/bark_notify.sh`（等于 `notify send`）和 `scripts/bark_config.py`（等于 `notify config`）继续可用。

## 一、什么时候发

只在用户这一次的请求、或这个 loop / 会话开头的指令里要求了才发。“记住以后都这样”只保存偏好，不代表以后所有任务都自动推送。

| 状态 `--status` | 什么时候 | 标题前缀 | 打扰程度 |
|---|---|---|---|
| `decide` | 要用户拍板，没有用户就进行不下去 | ⚠️ | timeSensitive：专注模式下也会亮屏 |
| `fail` | 失败了，自己修不了 | ❌ | timeSensitive |
| `stop` | 暂停、取消、额度用完、被迫停下 | ⏹️ | timeSensitive |
| `done` | 整件事做完并验证过 | ✅ | active：正常提醒 |
| `progress` | 用户点名要的进度节点（20%、某个阶段开始或结束） | ▶️ | active |
| `test` | 测试 | 🧪 | active |

没写 `--status` 时，脚本按标题开头的 emoji 自动判断。已有调用方写的是“⚠️ …”这类标题，打扰程度会自动跟着状态走。

**“需要我确认时 Bark 我”** 属于一条持续生效的规则：在整个会话或 loop 里一直有效，用户不用每轮重复。遇到下面任何一种情况，先发 `decide`，然后停下来等用户回复，不要替用户选：

- 选方案、选设计、选域名这类取舍；
- 要花钱，或费用和之前说的不一样；
- 对真实用户发邮件、发消息、发公告；
- 删数据、覆盖、强推、回滚这类不可逆操作；
- 需要用户登录、授权、扫码、续费，或者额度用完了。

不要发的：每个小步骤、可以自己判断的小事、没要求过的进度、同一个问题的第二遍（用 `--once`）。

## 二、怎么写

- **标题** 8–20 个字，写清什么事、什么状态，例如“#42 要你选方案”“120 个文件全部处理完”。前缀 emoji 由 `--status` 自动加。
- **正文** 最多 4 行，第一行就写结论或要用户做的事。
- **副标题** 自动填当前 git 仓库名或目录名，用来告诉用户是哪个项目、该回哪个会话。同时开着多个会话时，用 `--subtitle` 写得更具体，比如 `--subtitle "my-app · issue loop"`。设了环境变量 `XXD_NOTIFY_SOURCE` 时用它的值。
- **`--url`** 指向能看详情的页面（artifact、PR、issue、后台）。点开通知就直接到那里。
- **`decide` 的写法**：要你决定什么 → 选项（推荐的标出来）→ 去哪看 → 怎么回。

```bash
notify send -s decide -t "#42 要你选方案" --url "https://claude.ai/artifact/…" --once issue-42 \
  -b $'设置页的导出按钮放哪：\nA 顶栏右侧（推荐）\nB 页面底部\n回终端回复 A/B'

notify send -s done -t "数据迁移完成" \
  -b $'1.2 万条记录，核对一致\n用时 14 分钟'
```

不要写进通知的：Bark Key、密码、token、私密对话、大段原文。

**Shell 陷阱**：在 shell 脚本里，变量后面紧跟中文时一律写 `${var}`，比如 `"${reason}（登录）"`。macOS 自带的 bash 3.2 会把紧跟在 `$var` 后面的中文字符的第一个字节当成变量名的一部分，变量变成空值，中文也变成乱码。脚本会兜底照样发出，但那一段内容就丢了。

## 三、怎么发

```bash
notify send -s done -t "标题" -b "正文"          # 一条
notify run --title "跑测试" --tail 3 -- npm test  # 跑命令，结束时按退出码发 ✅ 或 ❌，退出码原样返回
notify watch --pid 12345 --name "批处理" \
  --log path/latest.log --stall 30 \
  --disk / --min-free 15                         # 进程结束发 ✅；日志 30 分钟不动、磁盘低于 15G 各提醒一次
notify watch --until "test -e out/DONE" --confirm 2 --interval 300 --name "上传"
```

**后台任务**（批处理、队列、screen 里的长任务）里，完成、卡住、磁盘这几项检测优先用 `run` 或 `watch`，不要每次手写。要放到后台时用 `nohup notify watch … &` 或开一个 screen。

脚本自己会：

- **重试**：最多 4 次，间隔 2、5、15 秒；
- **补发**：还是发不出去，就存进待补发，并在 Mac 上先弹一条本机通知；下一条通知发送成功时顺路补发；
- **去重**：同样的标题和正文 2 分钟内只发一次；`--once KEY` 让同一件事在 `--window` 分钟内（默认 60）只发一次。

所以调用方写 `|| true` 不会丢消息。

## 四、结果怎么判断

| 退出码 | 含义 |
|---|---|
| 0 | 已送达，stdout 是 Bark 返回的 JSON（`"code": 200`）；或者 stderr 输出了 `skipped`，表示和刚发过的重复，故意没发 |
| 2 | 参数不对 |
| 3 | 还没设置 Bark，消息已存进待补发 |
| 4 | Bark 拒收（多半是 Key 不对或被重置），消息已存进待补发 |
| 5 | 重试后仍连不上，消息已存进待补发，并弹了本机通知 |

只有退出码为 0 且不是 skipped 时，才告诉用户“已发送”。其他情况如实说明，并告诉用户 `notify history` 可以查看送达记录。

## 五、设置和测试

- **第一次设置**：Key 等于密码，不要让用户把 Key 贴进对话。请用户自己在终端运行：
  `! python3 <skill 目录>/scripts/xxd_notify.py setup`
  粘贴的内容不会显示在屏幕上。也可以 `pbpaste | python3 …/xxd_notify.py setup`。Bark App 里复制来的示例地址、只有 Key、自建服务器地址都能识别。setup 保存后会自动发一条测试通知。
- **测试**：`notify test`。
- **改偏好**：先运行 `notify config show`（Key 已遮住）给用户看当前配置，只改用户提到的项，例如 `notify config set sound birdsong`、`notify config set group "AI 任务"`。可以改的字段有：sound、group、level、icon、url、badge、isArchive、autoCopy、copy、autoSubtitle（填 0 关闭自动副标题）。
- **配置位置**：配置文件路径可以用环境变量 `XXD_BARK_CONFIG` 改；`XXD_BARK_ENDPOINT` 可以临时指定地址，适合 CI 或另一台机器。
- **配置缺失时**：不要编造 Key，按上面的“第一次设置”请用户运行 setup。

## 六、AI 额度重置提醒

盯着 Codex、Antigravity、Claude、Grok Bot 的额度重置：官方宣布要重置、正在重置时推一条，确认重置完再推一条。装之前已经发生过的重置不补推，还没落地的会马上推。

用户说“Codex/Claude/Antigravity/Grok 额度重置了提醒我”“盯着额度重置”时，直接装好，不用再问：

```bash
notify resets install --only claude,codex   # 用户点名哪几个就写哪几个（codex、antigravity、claude、grok-bot）；没点名就去掉 --only，四个都盯
notify resets check --dry-run               # 看各家现在的重置情况和会推什么，不发也不记
notify resets uninstall                     # 用户说“不用再提醒重置了”
```

- 还没设置 Bark 时，先按第五节请用户运行 setup，再 install。
- macOS 上 install 会装一个 launchd 后台任务（`~/Library/LaunchAgents/com.xxd-notify.resets.plist`），登录后自动跑。再运行一次 install 就换成新的名单。其他系统会打印一行 crontab，请用户自己加。
- 每 10 分钟从用户自己的电脑查一次 AIHOT 的公开接口。内容没变时接口只回一个空的 304，几乎不占流量。
- 连不上时只在 `resets.log` 里记一行，不会推送。日志和 `resets.json` 都在配置目录里。
- 个人非商业使用免费，条款见 https://aihot.news/terms。不要拿它做镜像、转发或收费服务。
