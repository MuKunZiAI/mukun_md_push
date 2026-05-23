---
name: mukun-md-push-wechat
description: 将 Markdown 文件转换为符合微信公众号规范的 HTML 文件，并可进一步推送到微信公众号草稿箱。支持日报模式（默认）、长文/历史故事模式（--essay）、AI 文章模式（--ai）。当用户提到"md转微信html""推送公众号""转换微信公众号格式"等意图时触发此技能。
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

## 技能 1：Markdown → 微信 HTML

调用脚本：
```bash
python3 ${CODEBUDDY_SKILL_DIR}/scripts/md2wechat_html.py <input.md> [output.html]
```

三种转换模式：
- **日报模式（默认）**：一条消息对应一条新闻，分四大板块，报纸风格配色
- **长文/历史故事模式（`--essay`）**：泛黄报纸风格背景，适合成语典故、历史故事类长文
- **AI 文章模式（`--ai`）**：白底灰字 + 棕色标签二级标题 + 固定尾栏，适合 AI 实践类文章

示例：
```bash
# 日报模式
python3 ${CODEBUDDY_SKILL_DIR}/scripts/md2wechat_html.py article.md article_wechat.html

# 长文模式
python3 ${CODEBUDDY_SKILL_DIR}/scripts/md2wechat_html.py --essay story.md story_wechat.html

# AI文章模式
python3 ${CODEBUDDY_SKILL_DIR}/scripts/md2wechat_html.py --ai ai_article.md ai_wechat.html
```

输出 HTML 文件保存在当前工作目录。若未指定 output.html，则根据模式自动生成文件名后缀（`_wechat.html`、`_essay_wechat.html`、`_ai_wechat.html`）。

## 技能 2：转换 + 推送草稿箱

调用脚本：
```bash
python3 ${CODEBUDDY_SKILL_DIR}/scripts/push_daily.py <input.md> [--title TITLE] [--cover COVER] [--digest DIGEST] [--media-id MEDIA_ID]
python3 ${CODEBUDDY_SKILL_DIR}/scripts/push_daily.py --essay <input.md> [--title TITLE] [--cover COVER] [--media-id MEDIA_ID]
python3 ${CODEBUDDY_SKILL_DIR}/scripts/push_daily.py --ai <input.md> [--title TITLE] [--cover COVER] [--media-id MEDIA_ID]
```

支持 Markdown frontmatter 提取标题和摘要：
```yaml
---
title: 文章标题
digest: 手动摘要（80字以内）
---
```

完整工作流：Markdown → HTML（复用技能1） → 上传封面图 → 推送草稿箱。

**自动拆分**：当 HTML 内容超过 20000 字符限制时，脚本会自动按 H2 标题拆分为多篇合并推送（同一图文消息内，读者上滑查看），标题自动添加（上）（中）（下）后缀。

## CSS 内联优化策略（字符节省）

微信公众号草稿接口有 **20000 字符限制**。脚本采用以下 CSS 继承策略压缩输出体积：

- **`text-indent:0`** 统一写到 `<body style>` 一次，全文继承，各 `<p>/<h2>/<h3>` 不再重复（`text-indent` 是可继承属性）
- **`color` / `font-size` / `line-height`** 提升到最近父级 `<section>`，子元素只保留差异化覆盖
- **`<td>` 的 `color`** 从 `<body>` 继承，不在每个 `td` 重复
- **空格规范**：style 属性内一律去掉冒号/分号后的空格，进一步节省

实测节省效果（示例文件）：
| 模式 | 优化前 | 优化后 | 节省 |
|------|--------|--------|------|
| 日报 | 9,324 字符 | 8,352 字符 | 972 字符 (10.4%) |
| AI文章 | 9,527 字符 | 9,101 字符 | 426 字符 (4.5%) |
| 长文 | 3,366 字符 | 3,156 字符 | 210 字符 (6.2%) |

## 前置检查

- 技能 1：无前置依赖
- 技能 2（推送草稿箱）：执行前**必须**确认配置文件 `~/.md_push_wechat/config.yaml` 存在。若不存在，**立即中断**，提示用户创建配置文件并填写 `appid` 和 `secret`，不得尝试从其他目录查找或自动创建。
