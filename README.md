# Agent Switchboard

A local-only switchboard for AI coding tool profiles.

Agent Switchboard 是一个单文件静态 Web 工具，用来在本机管理和切换 AI 编程工具的配置档案。它通过浏览器 File System Access API 读取和写回你主动选择的本地配置文件，不需要后端服务，也不会上传配置内容。

适合经常在不同模型、不同 API 网关、不同登录方式之间切换的开发者。

## 为什么需要它

很多 AI 编程工具的配置都保存在本地文件里。手动改配置容易出错，也不方便在多个环境之间切换。

Agent Switchboard 把这些本地配置整理成可命名的档案：

- 为 Claude Code、Codex CLI、OpenCode 分别维护配置档案
- 从当前本地配置文件导入已有环境
- 一键应用指定档案，写入前自动保存本地快照
- 导入、导出 Agent Switchboard 自身的档案库
- Codex CLI 支持 `config.toml` 模型路由、`auth_mode`、`auth.json` 登录缓存
- 无服务端、无数据库，配置只保存在浏览器本地存储和你授权的本地文件中

## 支持的配置文件

- Claude Code: `~/.claude/settings.json`
- Codex CLI config: `~/.codex/config.toml`
- Codex CLI auth: `~/.codex/auth.json`
- OpenCode: `~/.config/opencode/opencode.json`

## 浏览器要求

Agent Switchboard 依赖 File System Access API，需要使用支持该 API 的 Chromium 系浏览器，例如 Chrome 或 Edge。

本地预览建议通过 `localhost` 访问。线上部署需要 HTTPS，Vercel 默认提供 HTTPS。

## 快速开始

本项目没有构建步骤，直接启动静态文件服务即可。

```bash
python3 -m http.server 5173
```

打开：

```text
http://localhost:5173/
```

首次使用时，先在右侧绑定对应工具的配置文件。浏览器文件选择器中可以按 `Command + Shift + .` 显示隐藏目录。

## Vercel 部署

本仓库已包含 `vercel.json`，Vercel 会把根路径 `/` 重写到 `index.html`。

部署步骤：

1. 将仓库推送到 GitHub。
2. 在 Vercel 中导入该仓库。
3. Framework Preset 选择 `Other` 或 `No Framework`。
4. Build Command 留空。
5. Output Directory 使用默认根目录。
6. 部署完成后访问 Vercel 分配的 HTTPS 地址。

也可以使用 Vercel CLI：

```bash
vercel
vercel deploy --prod
```

## 安全说明

- Agent Switchboard 只会访问你主动选择授权的本地文件。
- 文件句柄保存在浏览器 IndexedDB 中，配置档案保存在 localStorage 中。
- 导出的 JSON 可能包含 API Key 或登录缓存，不要提交到公开仓库。
- 应用配置前会在 localStorage 中保存最近的文件快照，便于回看写入前状态。
- 静态托管服务只负责托管页面，不会接收或保存你的本地配置文件内容。

## 项目结构

```text
.
├── .gitignore
├── LICENSE
├── README.md
├── index.html
└── vercel.json
```

## 开发说明

当前项目保持为单文件实现，便于直接托管和审计。后续如果引入构建链，需要确保 File System Access API、权限提示、配置写回逻辑仍然可以在 HTTPS 环境下正常工作。

## 适合的仓库简介

```text
Local-only profile switcher for Claude Code, Codex CLI, and OpenCode.
```

中文简介：

```text
一个本地优先的 AI 编程工具配置档案切换器，支持 Claude Code、Codex CLI 和 OpenCode。
```

## 贡献

欢迎提交 Issue 或 Pull Request。比较适合的改进方向包括：

- 新增更多 AI 编程工具的配置适配
- 增加配置差异预览
- 增加备份恢复界面
- 改进移动端和窄屏布局

## License

MIT
