#!/usr/bin/env python3
"""
Markdown -> 微信兼容 HTML 转换器

支持三种模式：
  # 日报模式（默认）
  python3 md2wechat_html.py <input.md> [output.html]

  # 长文/历史故事模式（泛黄报纸风格）
  python3 md2wechat_html.py --essay <input.md> [output.html]

  # AI 类公众号文章模式（白底灰字 + 棕色标签标题）
  python3 md2wechat_html.py --ai <input.md> [output.html]

微信公众号 CSS 限制（实测记录）：
- 不支持：flex/grid布局、:root变量、clamp()、::before/::after伪元素、color-mix()
- 不支持：border-radius、double/dotted/dashed边框（回退为solid）
- 不支持：<a> 上的 border、<code> 上的 border
- 不支持：font-weight: 900（回退为700）、font-weight 在 <strong> 上的覆盖
- 会移除所有 <div> 标签，必须用 <section>
- <section> 上的 background/padding/margin 正常支持
- 表格：table/thead/tbody/colgroup 均支持
- letter-spacing 支持但有兼容差异，可保留
- 所有 CSS 必须内联到 style 属性
"""

import re
import sys
import os

# ─── 报纸风格配色 ──────────────────────────────────────
PAPER_BG      = "#f6f1e7"    # 报纸底色：泛黄暖白
PAPER_CARD    = "#faf7f0"    # 卡片底色：略浅的黄白
PAPER_DARK    = "#2c1810"    # 主文字色：深棕
PAPER_HEADING = "#3c2415"    # 标题色：焦棕
PAPER_ACCENT  = "#8b4513"    # 强调色：鞍褐
PAPER_RULE    = "#c4a882"    # 分隔线：浅棕
PAPER_MUTED   = "#8a7e6b"    # 辅助文字：灰棕
PAPER_CAPTION = "#a89880"    # 来源/脚注：淡棕
PAPER_HERO_BG = "#3c2415"    # 封面背景：深棕
PAPER_TABLE_BG = "#f0ead8"   # 表头底色

SECTION_COLORS = {
    "行业动态":              "#b8860b",
    "AI 工具与智能体更新":    "#556b2f",
    "AI 工具":              "#556b2f",
    "模型发布与更新":         "#4a3728",
    "模型发布":              "#4a3728",
    "重要研究进展":           "#2f4f4f",
    "研究进展":              "#2f4f4f",
    "今日要点总结":           "#3c2415",
    "本周要点总结":           "#3c2415",
}

# ─── HTML 模板（报纸风格，微信兼容） ────────────────────
# 使用 __PLACEHOLDER__ 避免与后续 .format() 的 {title} 等冲突

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body style="margin: 0; padding: 24px 16px; background: __PAPER_BG__; font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif">

<!-- 封面标题区：报纸报头风格 -->
<section style="background: __PAPER_HERO_BG__; padding: 24px 20px 20px; margin: 0 0 6px 0; border-top: 4px solid #c4a882">
  <p style="margin: 0 0 10px 0; font-size: 11px; color: #c4a882; letter-spacing: 2px; text-align: center; text-indent: 0">AI WEEKLY REVIEW</p>
  <h1 style="margin: 0; font-size: 22px; font-weight: bold; color: #faf7f0; line-height: 1.5; text-align: center; border: none">{title}</h1>
</section>

<!-- 信息来源栏：报头下的日期/来源 -->
<section style="background: __PAPER_CARD__; padding: 10px 16px; margin: 0 0 24px 0; border: 1px solid __PAPER_RULE__; border-top: none">
  <p style="margin: 0; font-size: 12px; color: __PAPER_MUTED__; line-height: 1.7; text-align: center; text-indent: 0; letter-spacing: 0.5px">{meta}</p>
</section>

{content}

<!-- 底部说明：报尾 -->
<section style="border-top: 2px solid __PAPER_RULE__; margin: 24px 0 0 0; padding: 12px 0 0 0; text-align: center">
  <p style="margin: 0; font-size: 11px; color: __PAPER_CAPTION__; text-indent: 0; letter-spacing: 1px">{footer}</p>
</section>

</body>
</html>"""

# 预替换颜色占位符，使模板可安全用于后续 .format({title}...)
for _name, _val in [
    ("PAPER_BG", PAPER_BG), ("PAPER_CARD", PAPER_CARD),
    ("PAPER_DARK", PAPER_DARK), ("PAPER_HEADING", PAPER_HEADING),
    ("PAPER_ACCENT", PAPER_ACCENT), ("PAPER_RULE", PAPER_RULE),
    ("PAPER_MUTED", PAPER_MUTED), ("PAPER_CAPTION", PAPER_CAPTION),
    ("PAPER_HERO_BG", PAPER_HERO_BG), ("PAPER_TABLE_BG", PAPER_TABLE_BG),
]:
    HTML_TEMPLATE = HTML_TEMPLATE.replace(f"__{_name}__", _val)


# ─── 解析 Markdown ─────────────────────────────────────

def parse_markdown(md_text):
    """解析日报 Markdown，返回结构化数据"""
    lines = md_text.strip().split('\n')

    title = ""
    meta = ""
    sections = []
    current_section = None
    current_items = []
    current_item = None
    in_table = False
    table_lines = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('# ') and not title:
            title = line[2:].strip()
            i += 1
            continue

        if line.startswith('> '):
            meta = line[2:].strip()
            i += 1
            continue

        if line == '---' or line == '***':
            if current_item:
                current_items.append(current_item)
                current_item = None
            if current_section and current_items:
                sections.append({"name": current_section, "items": current_items})
                current_items = []
            i += 1
            continue

        if line.startswith('## '):
            if current_item:
                current_items.append(current_item)
                current_item = None
            if current_section and current_items:
                sections.append({"name": current_section, "items": current_items})
                current_items = []
            current_section = line[3:].strip()
            i += 1
            continue

        if line.startswith('### '):
            if current_item:
                current_items.append(current_item)
            current_item = {
                "title": line[4:].strip(),
                "description": "",
                "source": "",
                "table": None
            }
            i += 1
            continue

        if line.startswith('|'):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(line)
            i += 1
            continue
        elif in_table and not line.startswith('|'):
            in_table = False
            if current_item:
                current_item["table"] = parse_table(table_lines)
            table_lines = []

        if line.startswith('来源：'):
            if current_item:
                current_item["source"] = line[3:].strip()
            i += 1
            continue

        if not line:
            i += 1
            continue

        if current_item:
            if current_item["description"]:
                current_item["description"] += " " + line
            else:
                current_item["description"] = line

        i += 1

    if in_table and table_lines and current_item:
        current_item["table"] = parse_table(table_lines)
    if current_item:
        current_items.append(current_item)
    if current_section and current_items:
        sections.append({"name": current_section, "items": current_items})

    footer = ""
    for line in lines:
        if line.strip().startswith('*') and line.strip().endswith('*'):
            footer = line.strip().strip('*').strip()
            break

    return {"title": title, "meta": meta, "sections": sections, "footer": footer}


def parse_table(table_lines):
    """解析 Markdown 表格为结构化数据"""
    rows = []
    headers = []

    for i, line in enumerate(table_lines):
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if i == 0:
            headers = cells
        elif i == 1:
            continue
        else:
            rows.append(cells)

    return {"headers": headers, "rows": rows}


# ─── 生成 HTML ─────────────────────────────────────────

def escape_html(text):
    """转义 HTML 特殊字符"""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text


def md_link_to_html(text):
    """将 Markdown 链接转为 HTML 链接（微信兼容：不加 border）"""
    def replace_link(m):
        link_text = m.group(1)
        link_url = m.group(2)
        return f'<a href="{link_url}" style="color: {PAPER_ACCENT}; text-decoration: none">{link_text}</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, text)


def md_bold_to_html(text):
    """将 Markdown 粗体转为 HTML（微信兼容：用 <b> 而非 <strong>，不额外设 font-weight）"""
    def replace_bold(m):
        return f'<b style="color: {PAPER_HEADING}">{m.group(1)}</b>'
    return re.sub(r'\*\*([^*]+)\*\*', replace_bold, text)


def md_code_to_html(text):
    """将 Markdown 行内代码转为 HTML（微信兼容：不加 border）"""
    def replace_code(m):
        code = m.group(1)
        return f'<code style="font-size: 12px; background: {PAPER_TABLE_BG}; color: {PAPER_ACCENT}; padding: 2px 6px">{code}</code>'
    return re.sub(r'`([^`]+)`', replace_code, text)


def format_text(text):
    """格式化 Markdown 文本为 HTML"""
    text = escape_html(text)
    text = md_link_to_html(text)
    text = md_bold_to_html(text)
    text = md_code_to_html(text)
    return text


def render_table(table_data):
    """渲染 Markdown 表格为微信兼容 HTML（报纸风格）"""
    if not table_data:
        return ""

    headers = table_data["headers"]
    rows = table_data["rows"]

    col_count = len(headers)
    if col_count == 3:
        col_widths = ["36%", "64%"]
    elif col_count == 2:
        col_widths = ["20%", "80%"]
    else:
        col_widths = [f"{100//col_count}%"] * col_count

    html = f'<table style="width: 100%; border-collapse: collapse; margin: 0; font-size: 13px; border: 1px solid {PAPER_RULE}">\n'

    html += '  <colgroup>\n'
    for w in col_widths:
        html += f'    <col style="width: {w}" />\n'
    html += '  </colgroup>\n'

    html += '  <thead>\n'
    html += f'    <tr style="background: {PAPER_TABLE_BG}">\n'
    for h in headers:
        html += f'      <th style="padding: 8px 10px; border: 1px solid {PAPER_RULE}; text-align: left; font-weight: bold; color: {PAPER_HEADING}; font-size: 12px; background: {PAPER_TABLE_BG}">{format_text(h)}</th>\n'
    html += '    </tr>\n'
    html += '  </thead>\n'

    html += '  <tbody>\n'
    for i, row in enumerate(rows):
        html += '    <tr>\n'
        for j, cell in enumerate(row):
            cell_html = format_text(cell)
            if '⭐' in cell:
                cell_html = re.sub(r'(\d{1,3}(?:,\d{3})*)', r'<span style="color: #b8860b; font-weight: bold">\1</span>', cell_html)
            border_bottom = f'; border-bottom: 1px solid #ede5d0' if i < len(rows) - 1 else ''
            html += f'      <td style="padding: 8px 10px; border: 1px solid {PAPER_RULE}; border-top: none; color: {PAPER_DARK}{border_bottom}">{cell_html}</td>\n'
        html += '    </tr>\n'
    html += '  </tbody>\n'
    html += '</table>\n'

    return html


def render_item(item, color):
    """渲染单条新闻为微信兼容 HTML 卡片（报纸专栏风格，微信安全）"""
    html = f'<section style="background: {PAPER_CARD}; padding: 16px; margin: 0 0 12px 0; border-left: 3px solid {color}; border-bottom: 1px solid #ede5d0">\n'

    # 标题：h3 不加额外 font-family，用系统默认
    html += f'  <h3 style="margin: 0 0 8px 0; font-size: 16px; font-weight: bold; color: {PAPER_HEADING}; line-height: 1.5; text-indent: 0">{format_text(item["title"])}</h3>\n'

    # 描述：正文
    if item["description"]:
        html += f'  <p style="margin: 0 0 8px 0; font-size: 15px; color: {PAPER_DARK}; line-height: 1.9; text-indent: 0">{format_text(item["description"])}</p>\n'

    # 表格
    if item["table"]:
        html += '  ' + render_table(item["table"]).replace('\n', '\n  ').rstrip() + '\n'

    # 来源
    if item["source"]:
        source_html = format_text(item["source"])
        html += f'  <p style="margin: 8px 0 0 0; font-size: 11px; color: {PAPER_CAPTION}; text-indent: 0; letter-spacing: 0.5px">来源：{source_html}</p>\n'

    html += '</section>\n'
    return html


def render_summary_table(item):
    """渲染要点总结表格（报纸风格，微信安全）"""
    if not item or not item.get("table"):
        return ""

    table_data = item["table"]
    headers = table_data["headers"]
    rows = table_data["rows"]

    html = f'<section style="background: {PAPER_CARD}; padding: 16px; border: 1px solid {PAPER_RULE}">\n'
    html += '  <table style="width: 100%; border-collapse: collapse; margin: 0; font-size: 14px">\n'
    html += '    <colgroup>\n'
    html += '      <col style="width: 18%" />\n'
    html += '      <col style="width: 82%" />\n'
    html += '    </colgroup>\n'
    html += '    <tbody>\n'

    cat_colors = {
        "行业": "#b8860b",
        "工具": "#556b2f",
        "模型": "#4a3728",
        "研究": "#2f4f4f",
    }

    for i, row in enumerate(rows):
        border = f' style="border-bottom: 1px solid {PAPER_RULE}"' if i < len(rows) - 1 else ''
        cat = row[0].strip('*').strip() if row else ""
        color = cat_colors.get(cat, PAPER_HEADING)
        content = format_text(row[1]) if len(row) > 1 else ""
        html += f'      <tr{border}>\n'
        html += f'        <td style="padding: 10px 0; font-weight: bold; color: {color}; font-size: 14px; background: {PAPER_CARD}; vertical-align: top; letter-spacing: 1px">{format_text(cat)}</td>\n'
        html += f'        <td style="padding: 10px 0; color: {PAPER_DARK}; line-height: 1.8; font-size: 14px; background: {PAPER_CARD}">{content}</td>\n'
        html += '      </tr>\n'

    html += '    </tbody>\n'
    html += '  </table>\n'
    html += '</section>\n'
    return html


def generate_wechat_html(data):
    """生成微信兼容 HTML（报纸风格，微信安全）"""
    sections_html = []

    for section in data["sections"]:
        section_name = section["name"]
        color = SECTION_COLORS.get(section_name, PAPER_ACCENT)

        # 分类标题：报纸栏目头，双线下划线改为实线
        section_html = f'<section style="margin: 0 0 12px 0">\n'
        section_html += f'  <h2 style="margin: 0; font-size: 18px; font-weight: bold; color: {PAPER_HEADING}; line-height: 1; padding: 0 0 8px 0; border-bottom: 2px solid {PAPER_HEADING}; letter-spacing: 2px">{section_name}</h2>\n'
        section_html += f'  <hr style="border: none; border-top: 1px solid {PAPER_RULE}; margin: 0" />\n'
        section_html += '</section>\n'

        # 总结或普通卡片
        if "总结" in section_name:
            if section["items"]:
                section_html += render_summary_table(section["items"][0])
        else:
            for item in section["items"]:
                section_html += render_item(item, color)

        # 板块间分隔线（最后一个板块不加），dashed 改为 solid
        if section != data["sections"][-1]:
            section_html += f'<hr style="border: none; border-top: 1px solid {PAPER_RULE}; margin: 20px 0" />\n'

        sections_html.append(section_html)

    content = '\n'.join(sections_html)

    return HTML_TEMPLATE.format(
        title=escape_html(data["title"]),
        meta=format_text(data["meta"]),
        content=content,
        footer=escape_html(data["footer"])
    )


# ─── 前置处理 ─────────────────────────────────────────────

def strip_frontmatter(md_text):
    """去掉 Markdown 文件开头的 YAML frontmatter（---...--- 区段）

    保留区段后的正文内容，用于后续解析。
    """
    if md_text.startswith("---"):
        parts = md_text.split("---", 2)
        if len(parts) >= 3:
            # 去掉 frontmatter 头尾的三个 -，保留中间正文
            body = parts[2].strip()
            # 去掉 frontmatter 结束后紧跟的空行
            return body.lstrip("\n")
    return md_text


# ─── AI 文章风格配色（参考木昆子公众号AI类文章样式）────────
AI_BG      = "#ffffff"    # 白底
AI_TEXT    = "rgb(85,85,85)"  # 灰字
AI_ACCENT  = "rgb(198,110,73)"  # 棕色强调
AI_TAG_BG  = "rgb(198,110,73)"  # 标题背景
AI_TAG_TXT = "#ffffff"    # 标题白字
AI_BOLD    = "rgb(51,51,51)"    # 加粗灰黑

# ─── AI 文章 HTML 模板（白底灰字 + 棕色标签标题）────────────
AI_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body style="margin:0;padding:20px 16px;background:{ai_bg};font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif">

<!-- 封面 -->
<section style="background:{ai_tag_bg};padding:24px 20px;margin:0 0 24px 0">
  <p style="margin:0 0 8px 0;font-size:11px;color:{ai_tag_txt};letter-spacing:2px;text-align:center;text-indent:0;opacity:0.8">AI 实践观察</p>
  <h1 style="margin:0;font-size:22px;font-weight:bold;color:{ai_tag_txt};line-height:1.5;text-align:center;text-indent:0">{title}</h1>
</section>

<!-- 正文区域：统一继承基础样式 -->
<section style="color:{ai_text};font-size:16px;line-height:2em;letter-spacing:1px;padding:0 4px 20px 4px">
{content}
</section>

</body>
</html>"""


# ─── 长文（成语/历史故事/AI文章）解析器 ───────────────────────────

def parse_essay(md_text):
    """
    解析长文叙事 Markdown，支持：
    - # H1 标题
    - > ... 引用块（所有 > 行均作为 blockquote）
    - ## H2 章节标题
    - --- 分隔线（忽略）
    - 普通段落（正文）
    - **粗体强调**
    - 表格（|...| 格式）
    - 代码块（```...```）
    返回 {"title": str, "blocks": [...]}
    """
    lines = md_text.strip().split('\n')
    title = ""
    blocks = []
    para_buf = []
    in_code_block = False
    code_lines = []
    table_lines = []
    in_table = False
    bq_buf = []
    in_blockquote = False

    def flush_para():
        if para_buf:
            text = ' '.join(para_buf).strip()
            if text:
                blocks.append({"type": "para", "text": text})
            para_buf.clear()

    def flush_table():
        if table_lines:
            blocks.append({"type": "table", "rows": table_lines.copy()})
            table_lines.clear()

    def flush_bq():
        if bq_buf:
            text = '\n'.join(bq_buf).strip()
            if text:
                blocks.append({"type": "blockquote", "text": text})
            bq_buf.clear()

    for line in lines:
        raw = line.rstrip()
        stripped = raw.strip()

        # 代码块开始/结束
        if stripped.startswith('```'):
            if in_code_block:
                # 代码块结束，保存代码内容
                blocks.append({"type": "code_block", "text": '\n'.join(code_lines)})
                code_lines.clear()
            else:
                flush_para()
                flush_table()
            in_code_block = not in_code_block
            continue

        if in_code_block:
            code_lines.append(stripped)
            continue

        # H1 标题
        if stripped.startswith('# ') and not stripped.startswith('## '):
            flush_para()
            flush_table()
            if not title:
                title = stripped[2:].strip()
            continue

        # 引用块（> 开头）
        if stripped.startswith('> '):
            flush_para()
            flush_table()
            if not in_blockquote:
                flush_bq()
                in_blockquote = True
            bq_buf.append(stripped[2:].strip())
            continue

        # 退出引用块状态（遇到非 > 开头的非空行）
        if in_blockquote:
            flush_bq()
            in_blockquote = False

        # H2 章节标题
        if stripped.startswith('## '):
            flush_para()
            flush_table()
            blocks.append({"type": "heading", "text": stripped[3:].strip(), "level": 2})
            continue

        # H3 子标题
        if stripped.startswith('### '):
            flush_para()
            flush_table()
            blocks.append({"type": "heading", "text": stripped[4:].strip(), "level": 3})
            continue

        # 分隔线 --- 忽略
        if stripped in ('---', '***', '* * *'):
            flush_para()
            flush_table()
            continue

        # 表格行
        if stripped.startswith('|'):
            # 判断是否为分隔行：每个单元格只能包含 -、:、空格（排除 playwright-cli、agent-browser 等含连字符的）
            def is_separator_row(cells):
                for c in cells:
                    s = c.strip()
                    if s and not all(ch in '-: ' for ch in s):
                        return False
                return True
            cells = stripped.split('|')[1:-1]
            if is_separator_row(cells):
                continue  # 跳过分隔行
            flush_para()
            if in_table:
                table_lines.append(stripped)
            else:
                in_table = True
                table_lines.append(stripped)
            continue
        elif in_table:
            flush_table()
            in_table = False

        # 空行：结束当前段落
        if not stripped:
            flush_para()
            continue

        # 普通段落行：累积
        para_buf.append(stripped)

    flush_para()
    flush_bq()
    if in_table:
        flush_table()
    return {"title": title, "blocks": blocks}


# ─── 长文 HTML 渲染 ─────────────────────────────────────

# 封面模板（历史风格，深棕背景）
ESSAY_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body style="margin:0;padding:20px 16px;background:__PAPER_BG__;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif">

<!-- 封面 -->
<section style="background:__PAPER_HERO_BG__;padding:28px 20px 22px;margin:0 0 0 0;border-top:4px solid __PAPER_RULE__">
  <p style="margin:0 0 8px 0;font-size:11px;color:__PAPER_RULE__;letter-spacing:3px;text-align:center;text-indent:0">成语典故 · 历史人物</p>
  <h1 style="margin:0 0 10px 0;font-size:24px;font-weight:bold;color:#faf7f0;line-height:1.4;text-align:center;border:none">{title}</h1>

</section>

<!-- 正文区域：统一继承字色/字号/行高，减少每段重复样式 -->
<section style="background:__PAPER_BG__;color:__PAPER_DARK__;font-size:16px;line-height:1.9;padding:20px 4px 8px 4px">
{content}
</section>

<!-- 页脚 -->
<section style="border-top:2px solid __PAPER_RULE__;margin:16px 0 0 0;padding:10px 0 0 0;text-align:center">
  <p style="margin:0;font-size:11px;color:__PAPER_CAPTION__;text-indent:0;letter-spacing:1px">{footer}</p>
</section>

</body>
</html>"""

for _name, _val in [
    ("PAPER_BG", PAPER_BG), ("PAPER_CARD", PAPER_CARD),
    ("PAPER_DARK", PAPER_DARK), ("PAPER_HEADING", PAPER_HEADING),
    ("PAPER_ACCENT", PAPER_ACCENT), ("PAPER_RULE", PAPER_RULE),
    ("PAPER_MUTED", PAPER_MUTED), ("PAPER_CAPTION", PAPER_CAPTION),
    ("PAPER_HERO_BG", PAPER_HERO_BG), ("PAPER_TABLE_BG", PAPER_TABLE_BG),
]:
    ESSAY_HTML_TEMPLATE = ESSAY_HTML_TEMPLATE.replace(f"__{_name}__", _val)


def generate_essay_html(data, footer="木昆子聊历史 · 成语典故系列"):
    """将 parse_essay 返回的结构渲染为微信兼容 HTML（极简内联样式）"""
    content_parts = []
    for block in data["blocks"]:
        btype = block["type"]
        text = block["text"]

        if btype == "heading" and block["level"] == 2:
            # H2：章节标题，棕色居中标签样式
            content_parts.append(
                f'<h2 style="margin:24px auto 16px;padding:6px 20px;font-size:18px;font-weight:bold;color:#fff;'
                f'background:{AI_ACCENT};text-align:center;border-radius:8px;'
                f'box-shadow:0 2px 6px rgba(0,0,0,0.1);display:block;width:fit-content;line-height:1.6;text-indent:0">'
                f'{format_text(escape_html(text))}</h2>'
            )
        elif btype == "heading" and block["level"] == 3:
            # H3：子标题，黑灰加粗
            content_parts.append(
                f'<p style="margin:20px 0 10px 0;font-size:16px;font-weight:bold;color:#333;text-indent:0">'
                f'{format_text(escape_html(text))}</p>'
            )
        elif btype == "para":
            # 普通段落：去掉缩进
            formatted = format_text(escape_html(text))
            content_parts.append(
                f'<p style="margin:0 0 14px 0;text-indent:0">{formatted}</p>'
            )

    content = '\n'.join(content_parts)
    return ESSAY_HTML_TEMPLATE.format(
        title=escape_html(data["title"]),
        content=content,
        footer=escape_html(footer)
    )


# ─── AI 文章 HTML 生成（白底灰字 + 棕色标签）────────────────

def ai_format_text(text):
    """AI 文章文本格式化"""
    text = escape_html(text)
    # 链接：棕色
    def replace_link(m):
        return f'<a href="{m.group(2)}" style="color:{AI_ACCENT};text-decoration:none">{m.group(1)}</a>'
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, text)
    # 粗体：加粗黑灰
    def replace_bold(m):
        return f'<b style="font-weight:bold;color:{AI_BOLD}">{m.group(1)}</b>'
    text = re.sub(r'\*\*([^*]+)\*\*', replace_bold, text)
    # 代码：浅灰背景
    def replace_code(m):
        return f'<code style="font-size:13px;background:#f5f5f5;color:{AI_ACCENT};padding:2px 6px">{m.group(1)}</code>'
    text = re.sub(r'`([^`]+)`', replace_code, text)
    return text


def render_ai_table(rows):
    """渲染表格为微信兼容 HTML（AI文章风格）

    微信公众号表格支持：
    - table/thead/tbody 支持
    - 简单边框 border: 1px solid
    - padding 正常
    - 不支持 border-radius
    """
    if not rows:
        return ""

    # 解析表头和内容行
    headers = [c.strip() for c in rows[0].split('|')[1:-1]]
    data_rows = []
    for row in rows[1:]:  # rows[0] 是表头，分隔行在 parse_essay 中已跳过
        cells = [c.strip() for c in row.split('|')[1:-1]]
        if cells:
            data_rows.append(cells)

    # 共享样式：padding 提到 tbody（微信支持），th/td 只保留差异化属性
    # border: 1px solid #ddd 是表格边框必需，保留在 th/td 上（跨浏览器兼容）
    base = 'padding:10px 12px;border:1px solid #ddd'
    html = '<table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:14px">\n'

    # 表头：背景 + 字号 + 字重差异，padding/border 继承 base
    html += '  <thead>\n'
    html += '    <tr>\n'
    for h in headers:
        html += f'      <th style="{base};background:#f8f8f8;font-weight:bold;color:{AI_BOLD};font-size:13px">{ai_format_text(h)}</th>\n'
    html += '    </tr>\n'
    html += '  </thead>\n'

    # 表体：背景 + 文字色差异，padding 继承自 tbody style
    html += '  <tbody style="padding:10px 12px">\n'
    for i, row in enumerate(data_rows):
        bg = '#fff' if i % 2 == 0 else '#fafafa'
        html += '    <tr>\n'
        for cell in row:
            html += f'      <td style="{base};background:{bg};color:{AI_TEXT}">{ai_format_text(cell)}</td>\n'
        html += '    </tr>\n'
    html += '  </tbody>\n'
    html += '</table>\n'

    return html


def render_ai_blockquote(text):
    """渲染引用块为微信兼容 HTML（AI文章风格）

    样式：浅灰背景 + 棕色左边框 + 斜体灰字，段落间换行显示。
    微信不支持 ::before 伪元素，边框直接用 border 实现。
    """
    formatted = ai_format_text(escape_html(text.replace('\n', '<br>')))
    html = (
        f'<section style="margin:16px 0;padding:14px 16px;background:#f8f8f8'
        f';border-left:4px solid {AI_ACCENT}">'
        f'<p style="margin:0;font-size:14px;font-style:italic;color:#888;line-height:1.9">{formatted}</p>'
        f'</section>'
    )
    return html


def render_ai_code_block(code):
    """渲染代码块为微信兼容 HTML（AI文章风格）

    微信公众号代码块处理方式：
    - 使用浅灰背景 + 深灰边框
    - 等宽字体
    - 横向滚动支持
    - 不支持 border-radius，使用圆角替代为直角
    """
    if not code:
        return ""

    # 转义HTML并保留换行
    escaped = escape_html(code)
    lines = escaped.split('\n')
    html_lines = []
    for line in lines:
        # 处理行内代码（反转换，因为已经转义）
        line = re.sub(r'&lt;code&gt;([^&]+)&lt;/code&gt;', r'<code>\1</code>', line)
        html_lines.append(line)

    code_html = '<br>'.join(html_lines)

    html = f'''<section style="background:#f6f8fa;border:1px solid #e1e4e8;margin:16px 0;padding:16px;overflow-x:auto">
  <code style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:13px;color:#24292e;line-height:1.6;white-space:pre">{code_html}</code>
</section>'''
    return html


def render_ai_ending():
    """生成 AI 类文章尾部通用尾栏（微信兼容，极简内联样式）

    结构：
      —End—
      如果觉得不错 随手点个 赞、在看、转发 三连吧
      关注+星标 可第一时间收到更多精彩思考和总结
      您的支持是我继续写下去的动力
      注：原创不易，合作请在公众号后台留言，未经许可，不得随意修改及盗用原文。

    样式策略：共有属性（字号、颜色、字间距、行高）提到父 section，
    各 p 标签只保留 margin，节省字符。
    """
    # 共有样式：字号、颜色、字间距、行高
    base_style = 'font-size:12px;color:#888;letter-spacing:0.5px;line-height:1.9'
    return (
        f'<section style="text-align:center;padding:24px 0 0 0;border-top:1px solid #eee;margin:20px 0 0 0;{base_style}">'
        '<p style="margin:0 0 10px 0">—End—</p>'
        '<p style="margin:0 0 10px 0">如果觉得不错 随手点个 <span style="color:#ff4c41">赞</span>、<span style="color:#ff2941">在看</span>、<span style="color:#ff4c41">转发</span> 三连吧</p>'
        '<p style="margin:0 0 10px 0"><span style="color:#ff2941">关注+星标</span> 可第一时间收到更多精彩思考和总结</p>'
        '<p style="margin:0 0 10px 0">您的支持是我继续写下去的动力</p>'
        '<p style="margin:0">注：原创不易，合作请在公众号后台留言，未经许可，不得随意修改及盗用原文。</p>'
        '</section>'
    )


def generate_ai_html(data):
    """生成 AI 类公众号文章 HTML（白底灰字 + 棕色标签标题）"""

    content_parts = []
    for block in data["blocks"]:
        btype = block["type"]

        if btype == "heading":
            text = block["text"]
            level = block["level"]
            if level == 2:
                # H2：棕色居中标签标题
                content_parts.append(
                    f'<h2 style="margin:28px auto 18px;padding:8px 24px;font-size:18px;font-weight:bold;color:#fff;'
                    f'background:{AI_ACCENT};text-align:center;display:block;'
                    f'width:fit-content;line-height:1.6;text-indent:0;box-shadow:0 2px 6px rgba(0,0,0,0.12)">'
                    f'{ai_format_text(escape_html(text))}</h2>'
                )
            else:
                # H3：灰黑加粗标题
                content_parts.append(
                    f'<p style="margin:22px 0 12px 0;font-size:16px;font-weight:bold;color:#333;text-indent:0;line-height:1.5">'
                    f'{ai_format_text(escape_html(text))}</p>'
                )
        elif btype == "table":
            # 表格
            content_parts.append(render_ai_table(block["rows"]))
        elif btype == "blockquote":
            # 引用块
            content_parts.append(render_ai_blockquote(block["text"]))
        elif btype == "code_block":
            # 代码块
            content_parts.append(render_ai_code_block(block["text"]))
        elif btype == "para":
            # 普通段落：默认无缩进，无需显式写 text-indent:0
            formatted = ai_format_text(escape_html(block["text"]))
            content_parts.append(
                f'<p style="margin:0 0 14px 0">{formatted}</p>'
            )

    content = '\n'.join(content_parts)

    # 尾栏
    ending = render_ai_ending()

    # 替换模板占位符
    html = AI_HTML_TEMPLATE.format(
        ai_bg=AI_BG,
        ai_text=AI_TEXT,
        ai_tag_bg=AI_TAG_BG,
        ai_tag_txt=AI_TAG_TXT,
        title=escape_html(data["title"]),
        content=content
    )
    # 尾栏追加到正文末尾（在最后一个 </section> 之后）
    html = html.replace('</section>\n\n</body>', f'</section>\n{ending}\n\n</body>')
    return html


# ─── 主入口 ─────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    mode = "daily"  # daily | essay | ai

    if args and args[0] == '--essay':
        mode = "essay"
        args = args[1:]
    elif args and args[0] == '--ai':
        mode = "ai"
        args = args[1:]

    if not args:
        print("用法:")
        print("  python3 md2wechat_html.py <input.md> [output.html]          # 日报模式")
        print("  python3 md2wechat_html.py --essay <input.md> [output.html]  # 长文/历史类模式（泛黄报纸风格）")
        print("  python3 md2wechat_html.py --ai <input.md> [output.html]     # AI文章模式（白底灰字+棕色标签）")
        sys.exit(1)

    md_file = args[0]
    if len(args) >= 2:
        output_file = args[1]
    else:
        base = os.path.splitext(md_file)[0]
        suffix_map = {"daily": "_wechat.html", "essay": "_essay_wechat.html", "ai": "_ai_wechat.html"}
        suffix = suffix_map.get(mode, "_wechat.html")
        output_file = f"{base}{suffix}"

    if not os.path.exists(md_file):
        print(f"ERROR: 文件不存在: {md_file}")
        sys.exit(1)

    with open(md_file, "r", encoding="utf-8") as f:
        md_text = f.read()

    # 去掉 frontmatter
    md_text = strip_frontmatter(md_text)

    if mode == "essay":
        data = parse_essay(md_text)
        html = generate_essay_html(data)
        print(f"生成成功（长文模式）: {output_file}")
        print(f"   标题: {data['title']}")
        print(f"   段落块数: {len(data['blocks'])}")
    elif mode == "ai":
        data = parse_essay(md_text)
        html = generate_ai_html(data)
        print(f"生成成功（AI文章模式）: {output_file}")
        print(f"   标题: {data['title']}")
        print(f"   段落块数: {len(data['blocks'])}")
    else:
        data = parse_markdown(md_text)
        html = generate_wechat_html(data)
        print(f"生成成功: {output_file}")
        print(f"   标题: {data['title']}")
        print(f"   板块数: {len(data['sections'])}")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    char_count = len(html)
    print(f"   总字符: {char_count}")
    if char_count > 20000:
        print(f"   ⚠️  警告: 字符数 {char_count} 超过微信公众号草稿接口限制（20000字符）！")
    else:
        print(f"   ✅ 字符数在微信限制内（{char_count}/20000）")


if __name__ == "__main__":
    main()
