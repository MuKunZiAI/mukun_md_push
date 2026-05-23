# mukun_md_push_wechat

将 Markdown 文件转换为符合微信公众号规范的 HTML 文件，并可一键推送到公众号草稿箱。

## 功能特性

- **三种转换模式**：日报模式（默认）、长文/历史故事模式（`--essay`）、AI 文章模式（`--ai`）
- **微信样式兼容**：所有 CSS 内联，使用 `<section>` 替代 `<div>`，规避微信渲染限制
- **草稿箱推送**：转换后直接上传到微信公众号草稿箱，手动补图即可发布
- **Frontmatter 支持**：可在 Markdown 文件顶部声明标题和摘要
- **多平台兼容**：同时支持 WorkBuddy、Claude Code、OpenCode、Codex CLI

## 安装

本 Skill 遵循通用的 `SKILL.md + scripts/` 结构，可安装到多个主流 AI 编程工具中。

> **注意**：各工具的 skill 目录名（`mukun-md-push-wechat`）即仓库中的 `SKILL.md` 文件夹名。

### WorkBuddy

```bash
# 用户级安装（所有项目可用）
git clone https://github.com/MuKunZiAI/mukun_md_push.git ~/.workbuddy/skills/mukun-md-push-wechat

# 项目级安装（仅当前项目可用）
git clone https://github.com/MuKunZiAI/mukun_md_push.git .workbuddy/skills/mukun-md-push-wechat
```

安装后在对话中直接描述需求即可自动触发（如"把这篇md转成微信html"）。

### Claude Code

```bash
# 用户级安装（所有项目可用）
git clone https://github.com/MuKunZiAI/mukun_md_push.git ~/.claude/skills/mukun-md-push-wechat

# 项目级安装（团队共享，提交到版本控制）
git clone https://github.com/MuKunZiAI/mukun_md_push.git .claude/skills/mukun-md-push-wechat
```

安装后通过 `/mukun-md-push-wechat` 手动触发，或由 Claude 根据描述自动加载。

### OpenCode

OpenCode 支持两种安装方式：

#### 方式一：Plugin 模式（推荐，支持自动更新）

在 `opencode.json`（全局或项目级别）中添加插件配置：

```json
{
  "plugin": ["mukun-md-push-wechat@git+https://github.com/MuKunZiAI/mukun_md_push.git"]
}
```

保存后重启 OpenCode，插件会自动安装并注册所有 skills。通过 `use skill tool to load mukun-md-push-wechat` 调用。

#### 方式二：npm 手动安装

适用于 OpenCode 插件管理器无法自动安装的环境（如部分 Windows 版本）：

```bash
npm install mukun-md-push-wechat@git+https://github.com/MuKunZiAI/mukun_md_push.git --prefix "$HOME/.config/opencode"
```

然后在 `opencode.json` 中指向本地包：

```json
{
  "plugin": ["~/.config/opencode/node_modules/mukun-md-push-wechat"]
}
```

#### 方式三：手动 clone（传统方式）

```bash
# 用户级安装
git clone https://github.com/MuKunZiAI/mukun_md_push.git ~/.opencode/skills/mukun-md-push-wechat

# 项目级安装
git clone https://github.com/MuKunZiAI/mukun_md_push.git .opencode/skills/mukun-md-push-wechat
```

安装后输入 `/init` 重新扫描加载，然后通过 `@mukun-md-push-wechat` 或自然语言触发。

> Plugin 模式下，插件会自动将仓库根目录注册为 skills 搜索路径，并注入 `CODEBUDDY_SKILL_DIR` 环境变量，确保 SKILL.md 中的脚本路径在 OpenCode 环境下也能正确解析。

### OpenAI Codex CLI

Codex CLI 使用 `AGENTS.md` 作为项目级指令文件，Skills 放在 `~/.codex/skills/` 目录下：

```bash
# 将 SKILL.md 复制到 Codex skills 目录
mkdir -p ~/.codex/skills/mukun-md-push-wechat
curl -o ~/.codex/skills/mukun-md-push-wechat/SKILL.md \
  https://raw.githubusercontent.com/MuKunZiAI/mukun_md_push/main/SKILL.md

# 如果需要脚本（转换 HTML 和推送功能依赖 Python 脚本）
git clone https://github.com/MuKunZiAI/mukun_md_push.git /tmp/mukun_md_push
cp -r /tmp/mukun_md_push/scripts ~/.codex/skills/mukun-md-push-wechat/
rm -rf /tmp/mukun_md_push
```

> Codex 的 Skills 是独立 `.md` 文件格式（Description / Input / Steps），而本 Skill 使用 `SKILL.md` + `scripts/` 结构。上述安装方式让 Codex 读取到 SKILL.md 中的指令内容，同时脚本可用于手动调用。

## 使用示例

仓库 `examples/` 目录下提供了三种模式的完整示例 Markdown 文件及其生成的 HTML 预览：

| 示例 | Markdown | HTML 预览 | 适用场景 |
|------|----------|-----------|---------|
| 日报模式 | [daily_example.md](examples/default/daily_example.md) | [daily_example.html](examples/default/daily_example.html) | AI 周报、行业动态汇总 |
| 长文模式 | [essay_example.md](examples/default/essay_example.md) | [essay_example.html](examples/default/essay_example.html) | 成语典故、历史故事 |
| AI文章模式 | [ai_article_example.md](examples/default/ai_article_example.md) | [ai_article_example.html](examples/default/ai_article_example.html) | 技术实践、AI 深度文章 |

#### 配色方案

除默认配色外，`examples/` 下还提供了两套自定义配色方案及对应示例：

| 配色方案 | 配置文件 | 示例预览 | 说明 |
|----------|----------|----------|------|
| 泛黄怀旧 | [config_nostalgic.yaml](examples/nostalgic/config_nostalgic.yaml) | [essay_nostalgic_example.html](examples/nostalgic/essay_nostalgic_example.html) | 深古卷泛黄 + 古铜暖棕，适合历史文章 |
| 现代化 | [config_modern.yaml](examples/modern/config_modern.yaml) | [ai_modern_example.html](examples/modern/ai_modern_example.html) | 科技蓝紫 + 深邃灰蓝，适合 AI 科技文章 |

使用自定义配色生成示例：

```bash
python3 scripts/md2wechat_html.py --config examples/nostalgic/config_nostalgic.yaml --essay story.md
python3 scripts/md2wechat_html.py --config examples/modern/config_modern.yaml --ai article.md
```

### 日报模式示例

一条消息对应一条新闻，分固定四大板块，报纸风格配色：

```markdown
# AI 周报 · 第12期

> 来源：木昆子AI实验室 | 2026-05-22

---

## 行业动态

### OpenAI 发布 GPT-5 Turbo
全新的 GPT-5 Turbo 在推理速度和准确率上均大幅提升...

来源：OpenAI Blog

---

## AI 工具与智能体更新
## 模型发布与更新
## 重要研究进展

---

## 本周要点总结

| 类别 | 要点 |
|------|------|
| 行业 | 大模型价格战持续 |
| 工具 | Cursor 4.0 和 Coze 2.0 发布 |
```

### 长文模式示例

泛黄报纸风格背景，适合叙事类长文：

```markdown
# 卧薪尝胆

> 春秋时期 · 越王勾践的复国之路

---

## 背景
勾践在夫椒之战中大败于吴王夫差...

## 受辱三年
在吴国期间，勾践表现得极为恭顺...

## 归国图强
回到越国后，勾践**卧薪尝胆**...

## 复仇灭吴
公元前473年，勾践率军大举伐吴...

## 成语释义
> **卧薪尝胆**：薪，柴草；胆，苦胆。形容人刻苦自励，发愤图强。
```

### AI文章模式示例

白底灰字 + 棕色标签二级标题，支持代码块、引用块、表格：

```markdown
---
title: 用 AI Agent 自动化你的周报工作流
digest: 从需求分析到落地部署，一步步构建自动化周报 Agent
---

# 用 AI Agent 自动化你的周报工作流

## 为什么要自动化周报
每周五下午写周报大概是程序员最头疼的事之一...

## 技术选型

| 环节 | 方案 | 理由 |
|------|------|------|
| 编排框架 | LangGraph | 支持复杂的状态机 |

## 收集模块的实现

```python
def collect_git_commits(repo_path: str, since: str):
    repo = git.Repo(repo_path)
    ...
```

> 如果你的团队使用 Conventional Commits 规范，收集后的信息质量会高很多。
```

## 使用方式

### 仅转换 HTML

```bash
# 日报模式（默认）
python3 scripts/md2wechat_html.py article.md

# 长文/成语故事模式
python3 scripts/md2wechat_html.py --essay story.md

# AI 文章模式
python3 scripts/md2wechat_html.py --ai ai_article.md

# 使用自定义配色配置
python3 scripts/md2wechat_html.py --config /path/to/my_theme.yaml --ai ai_article.md
```

### 转换 + 推送草稿箱

推送前需要配置 `~/.md_push_wechat/config.yaml`：

```yaml
wechat:
  appid: your_appid
  secret: your_secret
```

```bash
# 日报模式推送
python3 scripts/push_daily.py article.md

# 长文模式推送
python3 scripts/push_daily.py --essay story.md

# AI 文章模式推送
python3 scripts/push_daily.py --ai ai_article.md

# 自定义标题、封面图、摘要
python3 scripts/push_daily.py article.md --title "自定义标题" --cover ./封面图.png --digest "自定义摘要"
```

## 目录结构

```
mukun_md_push/
├── package.json                # NPM 包定义（OpenCode/Codex 插件安装）
├── SKILL.md                    # Skill 定义文件（各工具通用入口）
├── .opencode/
│   └── plugins/
│       └── mukun-md-push-wechat.js  # OpenCode 插件入口
├── scripts/
│   ├── md2wechat_html.py       # Markdown → 微信 HTML 转换器
│   └── push_daily.py           # 转换 + 推送草稿箱脚本
├── examples/
│   ├── default/                 # 默认配色示例
│   │   ├── daily_example.md
│   │   ├── daily_example.html
│   │   ├── essay_example.md
│   │   ├── essay_example.html
│   │   ├── ai_article_example.md
│   │   └── ai_article_example.html
│   ├── nostalgic/               # 泛黄怀旧配色方案（历史文章）
│   │   ├── config_nostalgic.yaml
│   │   └── essay_nostalgic_example.html
│   └── modern/                  # 现代化配色方案（AI 科技文章）
│       ├── config_modern.yaml
│       └── ai_modern_example.html
├── LICENSE
└── README.md
```

## 修改说明

### 2026-05-23

- **CSS 内联优化**：将 `text-indent`、`font-size`、`color`、`line-height` 等可继承属性提升到父级 `<body>`/`<section>`，减少重复声明。日报模式节省 10.4%，AI 模式节省 4.5%，长文模式节省 6.2%
- **超长文章自动拆分**：HTML 超过 20000 字符时按段落边界自动拆分为多篇，合并到同一个草稿推送，标题自动追加（上/中/下）后缀，智能截断保留后缀（`_truncate_title()`）
- **样式配置外部化**：`md2wechat_html.py` 新增 `load_style_config()` 从 `~/.md_push_wechat/config.yaml` 读取 `style` 节点覆盖内置默认值，支持 daily/ai/essay 三种模式独立配色，纯字符串解析 YAML 不引入额外依赖
- **`--config` 参数**：`md2wechat_html.py` 支持通过 `--config <path>` 指定任意配色配置文件
- **修复代码块缩进丢失**：`parse_essay()` 收集代码块行时改用 `raw`（保留行首空格），修复 YAML、文件树等缩进代码渲染后缩进丢失的问题
- **修复 YAML 值解析**：引号内的 `#` 颜色码不再被误判为注释，`load_style_config()` 正确读取自定义 `config_path` 参数
- **示例按配色方案分目录**：`examples/` 下新增 `default/`、`nostalgic/`（泛黄怀旧）、`modern/`（科技蓝紫）三个子目录，各含配置文件和示例 HTML

## License

MIT
