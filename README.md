<p align="center">
  <strong>mukun_md_push_wechat</strong><br/><br/>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.6+-green.svg" alt="Python 3.6+" /></a>
  <img src="https://img.shields.io/badge/WeChat-公众号推送-07C160?logo=wechat&logoColor=white" alt="WeChat" />
  <br/>
  <img src="https://img.shields.io/badge/WorkBuddy-支持-FF6B35?style=flat-square" alt="WorkBuddy" />
  <img src="https://img.shields.io/badge/Claude_Code-支持-D97757?style=flat-square&logo=anthropic&logoColor=white" alt="Claude Code" />
  <img src="https://img.shields.io/badge/OpenCode-支持-3B82F6?style=flat-square" alt="OpenCode" />
  <img src="https://img.shields.io/badge/Cursor-支持-7C3AED?style=flat-square" alt="Cursor" />
  <img src="https://img.shields.io/badge/Codex_CLI-支持-10A37F?style=flat-square&logo=openai&logoColor=white" alt="Codex CLI" />
</p>
<br/>

> 将 Markdown 文件转换为符合微信公众号规范的 HTML 文件，并可一键推送到公众号草稿箱。

## ✨ 功能特性

- 📰 **两种转换模式**：新闻模式（默认，板块化日报）和文章模式（长文叙事，配色可配置）
- 🎨 **微信样式兼容**：所有 CSS 内联，使用 `<section>` 替代 `<div>`，规避微信渲染限制
- 📤 **草稿箱推送**：转换后直接上传到微信公众号草稿箱，手动补图即可发布
- 📝 **Frontmatter 支持**：可在 Markdown 文件顶部声明标题和摘要
- 🔧 **多平台兼容**：同时支持 WorkBuddy、Claude Code、OpenCode、Codex CLI

## 📦 安装

本 Skill 遵循通用的 `SKILL.md + scripts/` 结构，可安装到多个主流 AI 编程工具中。

> **注意**：各工具的 skill 目录名（`mukun-md-push-wechat`）即仓库中的 `SKILL.md` 文件夹名。

### 通用方式（适用于任何 AI 智能体）

无需安装，直接在对话中把以下内容发给任意 AI 智能体：

```
请读取并安装这个 Skill：
https://raw.githubusercontent.com/MuKunZiAI/mukun_md_push/main/SKILL.md

然后再帮我把 <你的文件路径>.md 转换为微信公众号 HTML。
```

AI 会自动获取 SKILL.md 中的指令并按步骤执行，无需提前配置任何环境。适用于 WorkBuddy、Claude Code、OpenCode、Cursor、Gemini CLI 等所有支持联网读取的智能体。

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

## 💡 使用示例

仓库 `examples/` 目录下提供了两种模式的完整示例 Markdown 文件及其生成的 HTML 预览：

| 示例 | Markdown | HTML 预览 | 配色 | 适用场景 |
|------|----------|-----------|------|---------|
| 新闻模式 | [news_example.md](examples/default/news_example.md) | [news_example.html](examples/default/news_example.html) | 默认（报纸风格） | AI 周报、行业动态汇总 |
| 文章模式 | [article_example.md](examples/default/article_example.md) | [article_example.html](examples/default/article_example.html) | 默认（AI 风格） | 技术实践、AI 深度文章 |

#### 配色方案

除默认配色外，`examples/` 下还提供了两套自定义配色方案及对应示例：

| 配色方案 | 配置文件 | 示例源文件 | 示例预览 | 说明 |
|----------|----------|-----------|----------|------|
| 泛黄怀旧 | [config_nostalgic.yaml](examples/nostalgic/config_nostalgic.yaml) | [article_nostalgic_example.md](examples/nostalgic/article_nostalgic_example.md) | [article_nostalgic_example.html](examples/nostalgic/article_nostalgic_example.html) | 古卷泛黄 + 古铜暖棕，适合历史文章 |
| 现代化 | [config_modern.yaml](examples/modern/config_modern.yaml) | [article_example.md](examples/default/article_example.md) | [article_modern_example.html](examples/modern/article_modern_example.html) | 科技蓝紫 + 深邃灰蓝，适合 AI 科技文章 |

使用自定义配色生成示例：

```bash
python3 scripts/md2wechat_html.py --config examples/nostalgic/config_nostalgic.yaml --article story.md
python3 scripts/md2wechat_html.py --config examples/modern/config_modern.yaml --article article.md
```

> 完整配置示例参见 [examples/config_example.yaml](examples/config_example.yaml)，包含两种模式下所有可配置项及默认值注释。

### 🎨 样式配置参考

通过 `~/.md_push_wechat/config.yaml`（或 `--config` 参数）自定义样式。只有两种模式节点：`style.news` 和 `style.article`。

<details>
<summary><b>新闻模式（style.news）— 点击展开</b></summary>

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `bg` | `#f5f0e1` | 页面背景色（米黄报纸底色） |
| `card` | `#faf7f0` | 卡片/板块底色 |
| `dark` | `#3c2415` | 深色文字 |
| `heading` | `#3c2415` | 标题颜色 |
| `accent` | `#b8860b` | 强调色（板块名称标签） |
| `rule` | `#c9b99a` | 分隔线颜色 |
| `muted` | `#a08c6a` | 次要文字 |
| `caption` | `#a89880` | 脚注/报尾文字 |
| `hero_bg` | `#2c1810` | 封面标题区底色 |
| `table_bg` | `#f0ead8` | 表头底色 |
| `title_font_size` | `22px` | 文章主标题 |
| `text_font_size` | `15px` | 正文文字 |
| `h2_font_size` | `18px` | H2 板块标题 |
| `card_font_size` | `15px` | 板块内文字 |
| `cover_label` | `AI WEEKLY REVIEW` | 封面副标题 |
| `section_colors` | 见默认值 | 板块名→颜色映射（map） |
| `summary_colors` | 见默认值 | 总结表格类别→颜色映射（map） |
| `summary_sections` | `["总结"]` | 触发总结表格渲染的关键词列表 |

</details>

<details>
<summary><b>文章模式（style.article）— 点击展开</b></summary>

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `bg` | `#ffffff` | 页面背景色 |
| `text` | `rgb(85,85,85)` | 正文文字颜色 |
| `accent` | `rgb(198,110,73)` | 强调色（封面底色） |
| `hero_bg` | `rgb(198,110,73)` | 封面标题区底色 |
| `hero_title_color` | `#ffffff` | 封面标题文字颜色 |
| `bold` | `rgb(51,51,51)` | 加粗文字颜色 |
| `rule` | `#ddd` | 分隔线颜色 |
| `caption` | `#888` | 脚注/次要文字 |
| `title_font_size` | `22px` | 文章主标题 |
| `text_font_size` | `16px` | 正文文字 |
| `h2_font_size` | `18px` | H2 标题 |
| `cover_label` | `AI 实践观察` | 封面副标题 |
| `footer` | `""` | 底部署名（空字符串不显示） |
| `ending_lines` | 5 行默认尾栏 | 文末尾栏，`[]` 关闭，支持 HTML 标签 |

</details>

### 新闻模式

板块化日报，报纸风格配色：

<p align="center">
  <img src="assets/news.png" alt="新闻模式" width="480" />
</p>

### 文章模式（默认风格）

白底灰字 + 棕色标签二级标题，适合技术实践、AI 深度文章：

<p align="center">
  <img src="assets/article_default.png" alt="文章模式-默认" width="480" />
</p>

### 文章模式（泛黄怀旧）

古卷泛黄底色 + 古铜暖棕强调色，适合历史文化类叙事长文：

<p align="center">
  <img src="assets/article_nostalgic.png" alt="文章模式-泛黄怀旧" width="480" />
</p>

### 文章模式（科技蓝紫）

深邃灰蓝背景 + 蓝紫渐变强调色，适合 AI 科技、技术前沿文章：

<p align="center">
  <img src="assets/article_modern.png" alt="文章模式-科技蓝紫" width="480" />
</p>

## 🚀 使用方式

### 仅转换 HTML

```bash
# 新闻模式（默认）
python3 scripts/md2wechat_html.py article.md

# 文章模式
python3 scripts/md2wechat_html.py --article story.md

# 使用自定义配色配置
python3 scripts/md2wechat_html.py --config /path/to/my_theme.yaml --article article.md

# 或直接调用独立脚本
python3 scripts/md2news_html.py article.md
python3 scripts/md2article_html.py --config /path/to/my_theme.yaml story.md
```

### 转换 + 推送草稿箱

推送前需要配置 `~/.md_push_wechat/config.yaml`：

```yaml
wechat:
  appid: your_appid
  secret: your_secret
```

```bash
# 新闻模式推送
python3 scripts/push_daily.py article.md

# 文章模式推送
python3 scripts/push_daily.py --article story.md

# 自定义标题、封面图、摘要
python3 scripts/push_daily.py article.md --title "自定义标题" --cover ./封面图.png --digest "自定义摘要"
```

## 📁 目录结构

```
mukun_md_push/
├── package.json                # NPM 包定义（OpenCode/Codex 插件安装）
├── SKILL.md                    # Skill 定义文件（各工具通用入口）
├── .opencode/
│   └── plugins/
│       └── mukun-md-push-wechat.js  # OpenCode 插件入口
├── scripts/
│   ├── md2wechat_html.py       # 统一入口（模式路由 + 参数解析）
│   ├── md2news_html.py          # 新闻模式转换器
│   ├── md2article_html.py       # 文章模式转换器
│   └── push_daily.py            # 转换 + 推送草稿箱脚本
├── examples/
│   ├── config_example.yaml              # 完整配置示例（news + article 所有可配置项）
│   ├── default/                         # 默认配色示例（源文件 + 生成 HTML）
│   │   ├── news_example.md                   # 新闻模式源文件
│   │   ├── news_example.html                 # 新闻模式 HTML（生成，默认报纸配色）
│   │   ├── article_example.md                # 文章模式源文件（AI 技术实践）
│   │   ├── article_example.html              # 文章模式 HTML（生成，默认 AI 风格配色）
│   ├── nostalgic/                     # 泛黄怀旧配色方案（自含源文件+配置+HTML）
│   │   ├── config_nostalgic.yaml
│   │   ├── article_nostalgic_example.md      # 文章模式源文件（成语典故）
│   │   └── article_nostalgic_example.html    # 文章模式 HTML（生成，怀旧配色）
│   └── modern/                        # 现代化蓝紫配色方案
│       ├── config_modern.yaml
│       └── article_modern_example.html       # 文章模式 HTML（生成，使用 default/article_example.md 源文件）
├── LICENSE
└── README.md
```

## 📋 修改说明

### 2026-05-25

- **模式重构：三模式简化为两模式 + 文件重命名**
  - `md2news_html.py`：新闻模式（原 daily），独立脚本，板块化内容 + 报纸配色，通过 `style.news` 配置
  - `md2article_html.py`：文章模式（原 essay + ai 合并），统一长文渲染，默认 AI 风格配色（白底灰字），通过 `style.article` 配置可切换为泛黄怀旧等任意风格
  - `md2wechat_html.py`：统一入口（wrapper），负责模式路由和配置参数解析，`--news`/`--article` 标志，默认为 `--news`
  - 模板文件全部重命名：`daily_example.*` → `news_example.*`，`ai_article_example.*` → `article_example.*`，`essay_example.*` → `article_nostalgic_example.*`
- **push_daily.py 同步更新**：使用 `--article` 标志，封面图处理合并为统一的文章模式逻辑
- **配置结构调整**：`style.ai`/`style.essay` 统一为 `style.article`，example 配置文件同步更新
- **配置解析器增强**：新增 `ending_lines: []` 空列表支持，用于关闭文章模式尾栏
- **示例全部重新生成**：所有 HTML 预览文件用新脚本重新生成（daily→news 模式，essay/ai→article 模式+对应配色）
- **新增 `examples/config_example.yaml`**：完整配置示例，覆盖 news/article 两种模式下所有可配置项及默认值
- **README 新增样式配置参考章节**：折叠式展开两个模式的完整配置项表格，方便查阅
- **README/SKILL.md/package.json**：全部更新为两模式描述

### 2026-05-24

- **日报分类颜色可配置**：`SECTION_COLORS` 从硬编码改为从 `config.yaml` 的 `daily.section_colors` 读取。用 `板块名: 颜色值` 的 map 格式配置，配置后完整覆盖默认值，未匹配的板块名用 `accent` 兜底。使得「科技前沿」、「金融动态」等任意自定义板块名都能有独立配色
- **总结表格类别颜色可配置**：`render_summary_table()` 中 "行业/工具/模型/研究" 四个硬编码类别标签颜色改为从 `daily.summary_colors` 读取，支持完全自定义
- **总结板块判断可配置**：之前固定判断板块名包含「总结」才渲染为总结表格，改为从 `daily.summary_sections` 读取关键词列表（默认 `["总结"]`）。包含列表中任意关键词即触发总结渲染，支持「汇总」、「本期总结」等不同写法
- **YAML 解析器扩展**：`load_style_config()` 新增支持三级嵌套 map（`section_colors`/`summary_colors`）和列表（`summary_sections`），支持含中文的 key（板块名）
- **底部结尾文字全部可配置**：
  - daily 模式：封面副标题（默认 `"AI WEEKLY REVIEW"`）改为 `daily.cover_label` 可配置
  - ai 模式：尾栏固定文字（—End—、三连、关注+星标、支持感谢、版权声明）改为 `ai.ending_lines` 列表可配置，每项渲染为一个段落，支持内嵌 HTML 标签
  - essay 模式：`footer`（底部署名）与 `cover_label`（封面副标题）已可通过 `essay.footer` / `essay.cover_label` 配置（均含默认值）
- **推送摘要改为 AI 自动生成**：之前推送草稿箱时，若未手动指定 `--digest` 则直接截取正文前 120 字符，产生不完整无意义的截断。改为在 SKILL.md 中指示 AI agent 先读取文章内容、自动生成 120 字以内的精炼摘要再通过 `--digest` 传入。frontmatter 中已有 `digest` 时仍优先使用手动值

### 2026-05-23

- **CSS 内联优化**：将 `text-indent`、`font-size`、`color`、`line-height` 等可继承属性提升到父级 `<body>`/`<section>`，减少重复声明。日报模式节省 10.4%，AI 模式节省 4.5%，长文模式节省 6.2%
- **超长文章自动拆分**：HTML 超过 20000 字符时按段落边界自动拆分为多篇，合并到同一个草稿推送，标题自动追加（上/中/下）后缀，智能截断保留后缀（`_truncate_title()`）
- **样式配置外部化**：`md2wechat_html.py` 新增 `load_style_config()` 从 `~/.md_push_wechat/config.yaml` 读取 `style` 节点覆盖内置默认值，支持 daily/ai/essay 三种模式独立配色，纯字符串解析 YAML 不引入额外依赖
- **`--config` 参数**：`md2wechat_html.py` 支持通过 `--config <path>` 指定任意配色配置文件
- **修复代码块缩进丢失**：`parse_essay()` 收集代码块行时改用 `raw`（保留行首空格），修复 YAML、文件树等缩进代码渲染后缩进丢失的问题
- **修复 YAML 值解析**：引号内的 `#` 颜色码不再被误判为注释，`load_style_config()` 正确读取自定义 `config_path` 参数
- **示例按配色方案分目录**：`examples/` 下新增 `default/`、`nostalgic/`（泛黄怀旧）、`modern/`（科技蓝紫）三个子目录，各含配置文件和示例 HTML

## 📄 License

MIT
