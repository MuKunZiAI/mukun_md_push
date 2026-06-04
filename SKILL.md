---
name: mukun-md-push-wechat
description: 将 Markdown 文件转换为符合微信公众号规范的 HTML 文件，并可进一步推送到微信公众号草稿箱。支持文章模式（默认）和新闻模式。当用户提到"md转微信html""推送公众号""转换微信公众号格式"等意图时触发此技能。
allowed-tools: Read, Bash, Write
---

# Markdown 转微信公众号 HTML 并推送草稿箱

## 核心能力

将 Markdown 文件转换为符合微信公众号规范的 HTML 文件，支持三级标题、正文、粗体、链接、行内代码、代码块、引用块、表格等常用格式。所有 CSS 内联到 style 属性，确保微信渲染兼容。

支持进一步将转换后的 HTML 推送到微信公众号草稿箱。

## 场景决策

| 用户意图 | 执行方式 | 脚本命令 |
|---------|---------|---------|
| 「把这篇md转成微信html」「md转微信格式」「生成微信html」 | 仅转换 HTML | `${CODEBUDDY_SKILL_DIR}/scripts/md2wechat_html.py` |
| 「推送/发布到公众号」「先转换再推送到公众号」 | 转换 + 推送草稿箱 | `${CODEBUDDY_SKILL_DIR}/scripts/push_daily.py` |

**决策原则**：技能 2（推送）已包含技能 1（转换），无需同时调用两者。

**默认模式**：用户未明确指定时，使用文章模式（`--article`）。仅在以下情况使用新闻模式（`--news`）：
- 用户明确说"新闻模式""用新闻模式""--news"
- 上文对话已在讨论新闻日报、周报等内容
- Markdown 内容明显为板块化日报格式（含多个独立新闻板块）

**模式速查**：
| 模式 | 标志 | 独立脚本 | 适用场景 |
|------|------|---------|---------|
| 文章模式 | `--article`（默认） | `md2article_html.py` | 技术实践、成语典故、长文叙事（配色通过 config.yaml 控制）|
| 新闻模式 | `--news` | `md2news_html.py` | AI 周报、行业动态汇总（板块化日报，需用户明确指定）|

### 文章模式预设样式

文章模式内置 6 种预设样式，用户用自然语言描述即可自动匹配。每个预设对应 `references/` 目录下一个独立的 YAML 配置文件，既可被 SKILL.md 用自然语言匹配，也可直接通过 `--config` 传入脚本使用。

| 预设 | 配置文件 | 视觉特征 | 自然语言触发词（含任一即匹配） |
|------|---------|---------|--------------------------|
| 默认 | `references/article_default.yaml` | 白底灰字 + 棕橘胶囊标题 | 默认、默认样式、白色、白底、常规、简洁、干净、基础 |
| 泛黄怀旧 | `references/article_nostalgic.yaml` | 古卷泛黄底色 + 深棕胶囊标题 | 怀旧、泛黄、古风、古卷、黄底、暖黄、米黄底、历史、典籍、复古 |
| 科技蓝紫 | `references/article_modern.yaml` | 白底 + 蓝紫胶囊标题 + 深蓝封面 | 科技、蓝紫、科技蓝紫、蓝紫渐变、AI、技术、现代、前沿、潮流、深蓝封面 |
| 青绿引号 | `references/article_journal.yaml` | 米白底 + 青绿引号线 H2（大 Q + 引号包裹标题） | 青绿、青绿引号、引号标题、引号线、文艺、杂志、专栏、清爽、雅致、小清新 |
| 角标绿条 | `references/article_growth.yaml` | 白底 + 黄色编号角标 + 绿色标签块 H2 | 角标、角标绿条、角标编号、编号角标、badge、清单、步骤、运营、资讯、拆解、模块化、绿底封面 |
| 中轴蓝卡 | `references/article_blueprint.yaml` | 冷灰底 + 中轴蓝色编号卡 H2（居中编号 + 两侧横线） | 中轴、中轴蓝卡、中轴编号、编号卡、center、灰底、冷灰、蓝灰底、蓝色、产品文档、技术手册、结构化、规范、正式 |

**匹配规则**：
- 用户提及"默认样式"/"白色"/"白底"/"常规"/"简洁"/"干净"/"基础" → 使用 `${CODEBUDDY_SKILL_DIR}/references/article_default.yaml`
- 用户提及"怀旧"/"泛黄"/"古风"/"古卷"/"黄底"/"暖黄"/"米黄底"/"历史"/"典籍"/"复古" → 使用 `${CODEBUDDY_SKILL_DIR}/references/article_nostalgic.yaml`
- 用户提及"科技"/"蓝紫"/"科技蓝紫"/"蓝紫渐变"/"AI"/"技术"/"现代"/"前沿"/"潮流"/"深蓝封面" → 使用 `${CODEBUDDY_SKILL_DIR}/references/article_modern.yaml`
- 用户提及"青绿"/"青绿引号"/"引号标题"/"引号线"/"文艺"/"杂志"/"专栏"/"清爽"/"雅致"/"小清新" → 使用 `${CODEBUDDY_SKILL_DIR}/references/article_journal.yaml`
- 用户提及"角标"/"角标绿条"/"角标编号"/"编号角标"/"badge"/"清单"/"步骤"/"运营"/"资讯"/"拆解"/"模块化"/"绿底封面" → 使用 `${CODEBUDDY_SKILL_DIR}/references/article_growth.yaml`
- 用户提及"中轴"/"中轴蓝卡"/"中轴编号"/"编号卡"/"center"/"灰底"/"冷灰"/"蓝灰底"/"蓝色"/"产品文档"/"技术手册"/"结构化"/"规范"/"正式" → 使用 `${CODEBUDDY_SKILL_DIR}/references/article_blueprint.yaml`
- 用户未提及任何风格关键词 → **默认使用 `references/article_default.yaml`**

**执行方式**：识别到风格关键词后，通过 `--config` 参数传入对应的 reference 文件：
```bash
# 示例：用户说"用怀旧风格转成微信公众号 HTML"
python3 ${CODEBUDDY_SKILL_DIR}/scripts/md2wechat_html.py --config ${CODEBUDDY_SKILL_DIR}/references/article_nostalgic.yaml --article story.md

# 推送时同理
python3 ${CODEBUDDY_SKILL_DIR}/scripts/push_daily.py --config ${CODEBUDDY_SKILL_DIR}/references/article_nostalgic.yaml --article story.md --digest "..."
```

## 技能 1：Markdown → 微信 HTML

调用脚本：
```bash
python3 ${CODEBUDDY_SKILL_DIR}/scripts/md2wechat_html.py <input.md> [output.html]
```

两种转换模式：
- **文章模式（默认）**：长文叙事渲染，默认白底灰字 + 棕色标签标题，可通过 config.yaml 配置为泛黄报纸风格或任意自定义配色
- **新闻模式（`--news`）**：一条消息对应一条新闻，分板块展示，报纸风格配色（需用户明确指定）

示例：
```bash
# 文章模式（默认）
python3 ${CODEBUDDY_SKILL_DIR}/scripts/md2wechat_html.py story.md story_wechat.html

# 新闻模式（明确指定）
python3 ${CODEBUDDY_SKILL_DIR}/scripts/md2wechat_html.py --news article.md article_wechat.html

# 指定配置文件
python3 ${CODEBUDDY_SKILL_DIR}/scripts/md2wechat_html.py --config /path/to/config.yaml --article story.md
```

也可直接调用独立脚本：
```bash
python3 ${CODEBUDDY_SKILL_DIR}/scripts/md2news_html.py article.md
python3 ${CODEBUDDY_SKILL_DIR}/scripts/md2article_html.py --config /path/to/config.yaml story.md
```

输出 HTML 文件保存在当前工作目录。若未指定输出文件，则自动生成（`_news_wechat.html` 或 `_article_wechat.html`）。

## 技能 2：转换 + 推送草稿箱

调用脚本：
```bash
# 文章模式（默认）
python3 ${CODEBUDDY_SKILL_DIR}/scripts/push_daily.py <input.md> [--title TITLE] [--cover COVER] [--digest DIGEST] [--media-id MEDIA_ID]
# 新闻模式（明确指定）
python3 ${CODEBUDDY_SKILL_DIR}/scripts/push_daily.py --news <input.md> [--title TITLE] [--cover COVER] [--digest DIGEST] [--media-id MEDIA_ID]

# 更新已有草稿（追加 --update，注意 input.md 必须在 --update 之前，否则会被误判为 media_id）
python3 ${CODEBUDDY_SKILL_DIR}/scripts/push_daily.py <input.md> --update [--title TITLE] [--cover COVER] [--digest DIGEST]
python3 ${CODEBUDDY_SKILL_DIR}/scripts/push_daily.py <input.md> --update MEDIA_ID [--title TITLE] [--cover COVER] [--digest DIGEST]
python3 ${CODEBUDDY_SKILL_DIR}/scripts/push_daily.py --article <input.md> --update [--title TITLE] [--cover COVER] [--digest DIGEST]
python3 ${CODEBUDDY_SKILL_DIR}/scripts/push_daily.py --news <input.md> --update [--title TITLE] [--cover COVER] [--digest DIGEST]
```

支持 Markdown frontmatter 提取标题和摘要：
```yaml
---
title: 文章标题
digest: 手动摘要（80字以内）
---
```

### 完整工作流

**必须严格按以下步骤执行：**

1. **读取 Markdown 文件内容**（用 Read 工具）
2. **提取 frontmatter**：检查文件顶部是否有 `---` 包裹的 YAML 区段，提取 `title` 和 `digest` 字段
3. **生成摘要（重要！）**：如果 frontmatter 中没有 `digest` 字段，则**必须**根据文章正文内容自动生成一条 120 个字符以内的中文摘要，通过 `--digest` 参数传入脚本。摘要要求：
   - 简洁精炼，概括文章核心内容
   - 严格控制在 120 个字符以内（含标点）
   - 不要使用 markdown 格式或 HTML 标签
   - 不要以「本文」「这篇文章」开头
4. **调用 `push_daily.py`**：将生成的摘要通过 `--digest` 参数传入（若 frontmatter 已有 digest 则使用 frontmatter 中的值）
5. 脚本自动执行：Markdown → HTML → 上传封面图 → 上传正文图片素材 → 推送草稿箱

> **注意**：摘要生成是必选步骤，不可跳过。不要让脚本自动截取 120 字符——那会产生不完整的无意义截断。

**图片处理流程**（推送时自动执行）：
1. 从原始 Markdown 提取 `![](url)` 图片引用
2. 解析到本地文件（支持相对路径、绝对路径、alt 描述模糊匹配）
3. 计算文件内容 MD5，查缓存 `~/.md_push_wechat/config.yaml` 中 `image_cache.content`，命中则直接复用微信 CDN URL
4. 未命中则上传到微信永久素材库 `cgi-bin/material/add_material`
5. 将 HTML 中的 `src` 替换为微信 CDN URL，并保存缓存到 config.yaml

**封面图缓存**：
- 封面图 media_id 基于文件内容 MD5 缓存到 config.yaml 的 `image_cache.cover` 段
- 同一张封面图无论路径如何变化都会被识别并永久复用，无需重复上传

**草稿更新（`--update`）**：
- `--update [MEDIA_ID]`：更新已有草稿而非新建。MEDIA_ID 可选，不传则自动读取上次新建时保存的 `~/.md_push_wechat/draft_media_id.txt`
- 新闻/文章两种模式均支持更新

## 前置检查

- 技能 1：无前置依赖
- 技能 2（推送草稿箱）：执行前**必须**确认配置文件 `~/.md_push_wechat/config.yaml` 存在。若不存在，**立即中断**，提示用户创建配置文件并填写 `appid` 和 `secret`，不得尝试从其他目录查找或自动创建。
