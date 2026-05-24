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

# ─── 配置路径（默认，可通过 --config 覆盖）──────────────
CONFIG_PATH = os.path.join(os.path.expanduser("~/.md_push_wechat"), "config.yaml")

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

# 内置默认分类颜色（可在 config.yaml 的 daily.section_colors 中覆盖）
DEFAULT_SECTION_COLORS = {
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

# 内置默认要点总结表格的类别颜色（可在 config.yaml 的 daily.summary_colors 中覆盖）
DEFAULT_SUMMARY_COLORS = {
    "行业": "#b8860b",
    "工具": "#556b2f",
    "模型": "#4a3728",
    "研究": "#2f4f4f",
}

# 内置默认触发总结表格渲染的板块名称关键词列表
DEFAULT_SUMMARY_SECTIONS = ["总结"]

# ─── HTML 模板（报纸风格，微信兼容） ────────────────────
# 使用 __PLACEHOLDER__ 避免与后续 .format() 的 {title} 等冲突

_DAILY_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body style="margin:0;padding:24px 16px;background:__BG__;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;text-indent:0">

<!-- 封面标题区：报纸报头风格 -->
<section style="background:__HERO_BG__;padding:24px 20px 20px;margin:0 0 6px 0;border-top:4px solid __RULE__">
  <p style="margin:0 0 10px 0;font-size:11px;color:__RULE__;letter-spacing:2px;text-align:center">__COVER_LABEL__</p>
  <h1 style="margin:0;font-size:__TITLE_FONT_SIZE__;font-weight:bold;color:#faf7f0;line-height:1.5;text-align:center;border:none">{title}</h1>
</section>

<!-- 信息来源栏：报头下的日期/来源 -->
<section style="background:__CARD__;padding:10px 16px;margin:0 0 24px 0;border:1px solid __RULE__;border-top:none">
  <p style="margin:0;font-size:12px;color:__MUTED__;line-height:1.7;text-align:center;letter-spacing:0.5px">{meta}</p>
</section>

{content}

<!-- 底部说明：报尾 -->
<section style="border-top:2px solid __RULE__;margin:24px 0 0 0;padding:12px 0 0 0;text-align:center">
  <p style="margin:0;font-size:11px;color:__CAPTION__;letter-spacing:1px">{footer}</p>
</section>

</body>
</html>"""


def _build_daily_template(s):
    """用样式配置 s 替换日报模板占位符，返回可 .format() 的模板字符串"""
    t = _DAILY_TEMPLATE
    for name, val in [
        ("BG", s["bg"]), ("CARD", s["card"]),
        ("DARK", s["dark"]), ("HEADING", s["heading"]),
        ("ACCENT", s["accent"]), ("RULE", s["rule"]),
        ("MUTED", s["muted"]), ("CAPTION", s["caption"]),
        ("HERO_BG", s["hero_bg"]), ("TABLE_BG", s["table_bg"]),
        ("TITLE_FONT_SIZE", s["title_font_size"]),
        ("COVER_LABEL", s.get("cover_label", "AI WEEKLY REVIEW")),
    ]:
        t = t.replace(f"__{name}__", val)
    return t


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


def md_link_to_html(text, s=None):
    """将 Markdown 链接转为 HTML 链接（微信兼容：不加 border）"""
    accent = s["accent"] if s else PAPER_ACCENT
    def replace_link(m):
        link_text = m.group(1)
        link_url = m.group(2)
        return f'<a href="{link_url}" style="color: {accent}; text-decoration: none">{link_text}</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, text)


def md_bold_to_html(text, s=None):
    """将 Markdown 粗体转为 HTML（微信兼容：用 <b> 而非 <strong>，不额外设 font-weight）"""
    heading = s["heading"] if s else PAPER_HEADING
    def replace_bold(m):
        return f'<b style="color: {heading}">{m.group(1)}</b>'
    return re.sub(r'\*\*([^*]+)\*\*', replace_bold, text)


def md_code_to_html(text, s=None):
    """将 Markdown 行内代码转为 HTML（微信兼容：不加 border）"""
    table_bg = s.get("table_bg", PAPER_TABLE_BG) if s else PAPER_TABLE_BG
    accent = s["accent"] if s else PAPER_ACCENT
    def replace_code(m):
        code = m.group(1)
        return f'<code style="font-size: 12px; background: {table_bg}; color: {accent}; padding: 2px 6px">{code}</code>'
    return re.sub(r'`([^`]+)`', replace_code, text)


def format_text(text, s=None):
    """格式化 Markdown 文本为 HTML"""
    text = escape_html(text)
    text = md_link_to_html(text, s)
    text = md_bold_to_html(text, s)
    text = md_code_to_html(text, s)
    return text


def render_table(table_data, s):
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

    html = f'<table style="width:100%;border-collapse:collapse;margin:0;font-size:13px;border:1px solid {s["rule"]}">\n'

    html += '  <colgroup>\n'
    for w in col_widths:
        html += f'    <col style="width:{w}" />\n'
    html += '  </colgroup>\n'

    html += '  <thead>\n'
    html += f'    <tr style="background:{s["table_bg"]}">\n'
    for h in headers:
        html += f'      <th style="padding:8px 10px;border:1px solid {s["rule"]};text-align:left;font-weight:bold;color:{s["heading"]};font-size:12px;background:{s["table_bg"]}">{format_text(h, s)}</th>\n'
    html += '    </tr>\n'
    html += '  </thead>\n'

    html += '  <tbody>\n'
    for i, row in enumerate(rows):
        html += '    <tr>\n'
        for j, cell in enumerate(row):
            cell_html = format_text(cell, s)
            if '⭐' in cell:
                cell_html = re.sub(r'(\d{1,3}(?:,\d{3})*)', r'<span style="color:#b8860b;font-weight:bold">\1</span>', cell_html)
            border_bottom = f';border-bottom:1px solid #ede5d0' if i < len(rows) - 1 else ''
            html += f'      <td style="padding:8px 10px;border:1px solid {s["rule"]};border-top:none;color:{s["dark"]}{border_bottom}">{cell_html}</td>\n'
        html += '    </tr>\n'
    html += '  </tbody>\n'
    html += '</table>\n'

    return html


def render_item(item, color, s):
    """渲染单条新闻为微信兼容 HTML 卡片（报纸专栏风格，微信安全）

    body 已设 text-indent:0 可继承，卡片内各元素不再重复该属性。
    公共样式（font-size;color;line-height）提升到卡片 section，p 只剩 margin。
    """
    card_fs = s.get("card_font_size", s["text_font_size"])
    html = f'<section style="background:{s["card"]};padding:16px;margin:0 0 12px 0;border-left:3px solid {color};border-bottom:1px solid #ede5d0;font-size:{card_fs};color:{s["dark"]};line-height:1.9">\n'

    # 标题：h3 覆盖 font-size/color/line-height，其余继承
    html += f'  <h3 style="margin:0 0 8px 0;font-size:16px;font-weight:bold;color:{s["heading"]};line-height:1.5">{format_text(item["title"], s)}</h3>\n'

    # 描述：正文 — font-size/color/line-height 已从 section 继承，只剩 margin
    if item["description"]:
        html += f'  <p style="margin:0 0 8px 0">{format_text(item["description"], s)}</p>\n'

    # 表格
    if item["table"]:
        html += '  ' + render_table(item["table"], s).replace('\n', '\n  ').rstrip() + '\n'

    # 来源 — 小字注脚，需要覆盖 font-size/color
    if item["source"]:
        source_html = format_text(item["source"], s)
        html += f'  <p style="margin:8px 0 0 0;font-size:11px;color:{s["caption"]};letter-spacing:0.5px">来源：{source_html}</p>\n'

    html += '</section>\n'
    return html


def render_summary_table(item, s):
    """渲染要点总结表格（报纸风格，微信安全）"""
    if not item or not item.get("table"):
        return ""

    table_data = item["table"]
    headers = table_data["headers"]
    rows = table_data["rows"]

    html = f'<section style="background:{s["card"]};padding:16px;border:1px solid {s["rule"]}">\n'
    html += '  <table style="width:100%;border-collapse:collapse;margin:0;font-size:14px">\n'
    html += '    <colgroup>\n'
    html += '      <col style="width:18%" />\n'
    html += '      <col style="width:82%" />\n'
    html += '    </colgroup>\n'
    html += '    <tbody>\n'

    # 使用来自样式配置的总结颜色（可在 config.yaml 中自定义）
    cat_colors = s.get("summary_colors", DEFAULT_SUMMARY_COLORS)

    for i, row in enumerate(rows):
        border = f' style="border-bottom:1px solid {s["rule"]}"' if i < len(rows) - 1 else ''
        cat = row[0].strip('*').strip() if row else ""
        color = cat_colors.get(cat, s["heading"])
        content = format_text(row[1], s) if len(row) > 1 else ""
        html += f'      <tr{border}>\n'
        html += f'        <td style="padding:10px 0;font-weight:bold;color:{color};font-size:14px;background:{s["card"]};vertical-align:top;letter-spacing:1px">{format_text(cat, s)}</td>\n'
        html += f'        <td style="padding:10px 0;color:{s["dark"]};line-height:1.8;font-size:14px;background:{s["card"]}">{content}</td>\n'
        html += '      </tr>\n'

    html += '    </tbody>\n'
    html += '  </table>\n'
    html += '</section>\n'
    return html


def generate_wechat_html(data, s=None):
    """生成微信兼容 HTML（报纸风格，微信安全）"""
    if s is None:
        s = load_style_config()["daily"]

    sections_html = []

    for section in data["sections"]:
        section_name = section["name"]
        # 从样式配置读取分类颜色（可在 config.yaml 中自定义）
        section_colors = s.get("section_colors", DEFAULT_SECTION_COLORS)
        color = section_colors.get(section_name, s["accent"])

        # 分类标题：报纸栏目头
        section_html = f'<section style="margin:0 0 12px 0">\n'
        section_html += f'  <h2 style="margin:0;font-size:{s["h2_font_size"]};font-weight:bold;color:{s["heading"]};line-height:1;padding:0 0 8px 0;border-bottom:2px solid {s["heading"]};letter-spacing:2px">{section_name}</h2>\n'
        section_html += f'  <hr style="border:none;border-top:1px solid {s["rule"]};margin:0" />\n'
        section_html += '</section>\n'

        # 判断是否为总结板块（从样式配置读取，可在 config.yaml 中自定义）
        summary_sections = s.get("summary_sections", DEFAULT_SUMMARY_SECTIONS)
        is_summary = any(kw in section_name for kw in summary_sections)

        # 总结或普通卡片
        if is_summary:
            if section["items"]:
                section_html += render_summary_table(section["items"][0], s)
        else:
            for item in section["items"]:
                section_html += render_item(item, color, s)

        # 板块间分隔线（最后一个板块不加）
        if section != data["sections"][-1]:
            section_html += f'<hr style="border:none;border-top:1px solid {s["rule"]};margin:20px 0" />\n'

        sections_html.append(section_html)

    content = '\n'.join(sections_html)

    template = _build_daily_template(s)
    return template.format(
        title=escape_html(data["title"]),
        meta=format_text(data["meta"], s),
        content=content,
        footer=escape_html(data["footer"])
    )


# ─── 样式配置加载 ─────────────────────────────────────

def load_style_config(config_path=None):
    """从 config.yaml 读取 style 配置，与内置默认值合并

    config_path: 可选，指定配置文件路径（默认使用 CONFIG_PATH）

    返回三级字典: {"daily": {...}, "ai": {...}, "essay": {...}}
    每个模式包含颜色、字号、标签文字等配置项。
    config.yaml 中未写的字段自动回退到代码默认值，无需全部列出。
    """
    if config_path is None:
        config_path = CONFIG_PATH
    defaults = {
        "daily": {
            "bg": PAPER_BG,
            "card": PAPER_CARD,
            "dark": PAPER_DARK,
            "heading": PAPER_HEADING,
            "accent": PAPER_ACCENT,
            "rule": PAPER_RULE,
            "muted": PAPER_MUTED,
            "caption": PAPER_CAPTION,
            "hero_bg": PAPER_HERO_BG,
            "table_bg": PAPER_TABLE_BG,
            "title_font_size": "22px",
            "text_font_size": "15px",
            "h2_font_size": "18px",
            "card_font_size": "15px",
            "cover_label": "AI WEEKLY REVIEW",          # 封面副标题
            # 分类配置（可在 config.yaml 中覆盖）
            "section_colors": dict(DEFAULT_SECTION_COLORS),   # 板块名 -> 颜色
            "summary_colors": dict(DEFAULT_SUMMARY_COLORS),   # 总结表格类别标签 -> 颜色
            "summary_sections": list(DEFAULT_SUMMARY_SECTIONS),  # 触发总结渲染的关键词
        },
        "ai": {
            "bg": AI_BG,
            "text": AI_TEXT,
            "accent": AI_ACCENT,
            "tag_bg": AI_TAG_BG,
            "tag_txt": AI_TAG_TXT,
            "bold": AI_BOLD,
            "title_font_size": "22px",
            "text_font_size": "16px",
            "h2_font_size": "18px",
            "cover_label": "AI 实践观察",
            # 文章尾栏文字（可在 config.yaml 中覆盖，每行为一个列表项）
            "ending_lines": [
                "—End—",
                "如果觉得不错 随手点个 <span style=\"color:#ff4c41\">赞</span>、<span style=\"color:#ff2941\">在看</span>、<span style=\"color:#ff4c41\">转发</span> 三连吧",
                "<span style=\"color:#ff2941\">关注+星标</span> 可第一时间收到更多精彩思考和总结",
                "您的支持是我继续写下去的动力",
                "注：原创不易，合作请在公众号后台留言，未经许可，不得随意修改及盗用原文。",
            ],
        },
        "essay": {
            "bg": PAPER_BG,
            "card": PAPER_CARD,
            "dark": PAPER_DARK,
            "heading": PAPER_HEADING,
            "accent": AI_ACCENT,
            "bold": AI_BOLD,
            "rule": PAPER_RULE,
            "caption": PAPER_CAPTION,
            "hero_bg": PAPER_HERO_BG,
            "title_font_size": "24px",
            "text_font_size": "16px",
            "h2_font_size": "18px",
            "cover_label": "成语典故 · 历史人物",
            "footer": "木昆子聊历史 · 成语典故系列",
        },
    }

    # 读取 config.yaml 中的 style 节点（纯字符串解析，不依赖 pyyaml）
    if not os.path.exists(config_path):
        return defaults

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return defaults

    # 定位 style: 节点
    style_match = re.search(r'^style\s*:', content, re.MULTILINE)
    if not style_match:
        return defaults

    # 解析 style 下的 key: value 对
    # 支持结构：
    #   style:
    #     daily:
    #       accent: "#xxx"
    #       section_colors:          # map 子结构
    #         行业动态: "#b8860b"
    #       summary_sections:        # 列表子结构
    #         - 总结
    #         - 汇总
    style_block = content[style_match.start():]
    mode = None         # 当前模式：daily/ai/essay
    sub_map = None      # 当前正在填充的子 map key（如 section_colors）
    sub_is_list = False # 当前子结构是否是列表
    list_initialized = set()  # 记录已被用户覆盖初始化的 "mode.key" 列表

    def _parse_value(raw_v):
        """解析 YAML 值，支持引号、颜色码、去掉行尾注释"""
        raw_v = raw_v.strip()
        if raw_v and raw_v[0] in ('"', "'"):
            end_q = raw_v.find(raw_v[0], 1)
            if end_q > 0:
                return raw_v[1:end_q]
            return raw_v[1:].rstrip('"\'')
        comment_pos = raw_v.find(' #')
        if comment_pos >= 0:
            return raw_v[:comment_pos].strip()
        return raw_v

    for line in style_block.splitlines():
        raw_line = line
        stripped = raw_line.strip()

        # 遇到非 style 子节点的一级 key（不缩进），停止解析
        if stripped and not stripped.startswith('#') and ':' in stripped and not raw_line.startswith(' ') and not raw_line.startswith('\t'):
            key = stripped.split(':')[0].strip()
            if key == 'style':
                continue
            else:
                break  # 遇到 wechat 等其他一级节点，退出

        if not stripped or stripped.startswith('#'):
            continue

        # 检测模式名（如 "  daily:" 或 "    daily:"）
        mode_match = re.match(r'^(daily|ai|essay)\s*:\s*$', stripped)
        if mode_match:
            mode = mode_match.group(1)
            sub_map = None
            sub_is_list = False
            continue

        if not mode or mode not in defaults:
            continue

        # 检测列表项（"- value"）
        if stripped.startswith('- ') and sub_map and sub_is_list:
            list_key = f"{mode}.{sub_map}"
            if list_key not in list_initialized:
                defaults[mode][sub_map] = []  # 首次写入时清空默认值
                list_initialized.add(list_key)
            v = _parse_value(stripped[2:])
            if v:
                defaults[mode][sub_map].append(v)
            continue

        # 检测子 map/list key 行（无值，如 "section_colors:"）
        sub_key_match = re.match(r'^(\w+)\s*:\s*$', stripped)
        if sub_key_match:
            k = sub_key_match.group(1)
            if k in defaults[mode] and isinstance(defaults[mode][k], dict):
                sub_map = k
                sub_is_list = False
                defaults[mode][k] = {}  # 清空默认，用户完整覆盖
            elif k in defaults[mode] and isinstance(defaults[mode][k], list):
                sub_map = k
                sub_is_list = True
                # 列表在首个 "- " 行时才清空（此处仅标记进入状态）
            else:
                sub_map = None
                sub_is_list = False
            continue

        # 检测普通 ASCII key: value
        kv_match = re.match(r'^(\w+)\s*:\s*(.+)$', stripped)
        if kv_match:
            k, raw_v = kv_match.group(1), kv_match.group(2)
            v = _parse_value(raw_v)
            # 在子 map 内（如 section_colors 的条目）
            if sub_map and not sub_is_list and sub_map in defaults[mode]:
                defaults[mode][sub_map][k] = v
                continue
            # 退出子结构
            sub_map = None
            sub_is_list = False
            if k in defaults[mode]:
                defaults[mode][k] = v
            continue

        # 含中文的 key: value（如板块名 "行业动态: #xxx"）
        cn_kv = re.match(r'^(.+?)\s*:\s*(.+)$', stripped)
        if cn_kv and sub_map and not sub_is_list:
            k = cn_kv.group(1).strip()
            v = _parse_value(cn_kv.group(2))
            if sub_map in defaults[mode] and isinstance(defaults[mode][sub_map], dict):
                defaults[mode][sub_map][k] = v

    return defaults


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
<body style="margin:0;padding:20px 16px;background:{ai_bg};font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;text-indent:0;color:{ai_text}">

<!-- 封面 -->
<section style="background:{ai_tag_bg};padding:24px 20px;margin:0 0 24px 0">
  <p style="margin:0 0 8px 0;font-size:11px;color:{ai_tag_txt};letter-spacing:2px;text-align:center;opacity:0.8">{cover_label}</p>
  <h1 style="margin:0;font-size:{title_font_size};font-weight:bold;color:{ai_tag_txt};line-height:1.5;text-align:center">{title}</h1>
</section>

<!-- 正文区域：统一继承基础样式 -->
<section style="font-size:{text_font_size};line-height:2em;letter-spacing:1px;padding:0 4px 20px 4px">
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
            code_lines.append(raw)
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
_ESSAY_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body style="margin:0;padding:20px 16px;background:__BG__;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;text-indent:0">

<!-- 封面 -->
<section style="background:__HERO_BG__;padding:28px 20px 22px;margin:0 0 0 0;border-top:4px solid __RULE__">
  <p style="margin:0 0 8px 0;font-size:11px;color:__RULE__;letter-spacing:3px;text-align:center">{cover_label}</p>
  <h1 style="margin:0 0 10px 0;font-size:__TITLE_FONT_SIZE__;font-weight:bold;color:#faf7f0;line-height:1.4;text-align:center;border:none">{title}</h1>

</section>

<!-- 正文区域：统一继承字色/字号/行高，减少每段重复样式 -->
<section style="background:__BG__;color:__DARK__;font-size:__TEXT_FONT_SIZE__;line-height:1.9;padding:20px 4px 8px 4px">
{content}
</section>

<!-- 页脚 -->
<section style="border-top:2px solid __RULE__;margin:16px 0 0 0;padding:10px 0 0 0;text-align:center">
  <p style="margin:0;font-size:11px;color:__CAPTION__;letter-spacing:1px">{footer}</p>
</section>

</body>
</html>"""


def _build_essay_template(s):
    """用样式配置 s 替换长文模板占位符"""
    t = _ESSAY_TEMPLATE
    for name, val in [
        ("BG", s["bg"]), ("DARK", s["dark"]),
        ("HEADING", s["heading"]), ("ACCENT", s["accent"]),
        ("RULE", s["rule"]), ("CAPTION", s["caption"]),
        ("HERO_BG", s["hero_bg"]),
        ("TITLE_FONT_SIZE", s["title_font_size"]),
        ("TEXT_FONT_SIZE", s["text_font_size"]),
    ]:
        t = t.replace(f"__{name}__", val)
    return t


def generate_essay_html(data, s=None, footer=None):
    """将 parse_essay 返回的结构渲染为微信兼容 HTML（极简内联样式）"""
    if s is None:
        s = load_style_config()["essay"]
    if footer is None:
        footer = s.get("footer", "木昆子聊历史 · 成语典故系列")

    content_parts = []
    for block in data["blocks"]:
        btype = block["type"]
        text = block.get("text", "")

        if btype == "heading" and block["level"] == 2:
            # H2：章节标题，棕色居中标签样式（text-indent:0 从 body 继承）
            content_parts.append(
                f'<h2 style="margin:24px auto 16px;padding:6px 20px;font-size:{s["h2_font_size"]};font-weight:bold;color:#fff;'
                f'background:{s["accent"]};text-align:center;border-radius:8px;'
                f'box-shadow:0 2px 6px rgba(0,0,0,0.1);display:block;width:fit-content;line-height:1.6">'
                f'{format_text(escape_html(text), s)}</h2>'
            )
        elif btype == "heading" and block["level"] == 3:
            # H3：子标题，黑灰加粗（text-indent:0 从 body 继承）
            content_parts.append(
                f'<p style="margin:20px 0 10px 0;font-size:16px;font-weight:bold;color:#333">'
                f'{format_text(escape_html(text), s)}</p>'
            )
        elif btype == "blockquote":
            content_parts.append(render_ai_blockquote(text, s))
        elif btype == "code_block":
            content_parts.append(render_ai_code_block(text))
        elif btype == "table":
            content_parts.append(render_ai_table(block["rows"], s))
        elif btype == "para":
            # 普通段落：text-indent:0 从 body 继承，只保留 margin
            formatted = format_text(escape_html(text), s)
            content_parts.append(
                f'<p style="margin:0 0 14px 0">{formatted}</p>'
            )

    content = '\n'.join(content_parts)

    template = _build_essay_template(s)
    return template.format(
        title=escape_html(data["title"]),
        content=content,
        footer=escape_html(footer),
        cover_label=s.get("cover_label", "成语典故 · 历史人物")
    )


# ─── AI 文章 HTML 生成（白底灰字 + 棕色标签）────────────────

def ai_format_text(text, s=None):
    """AI 文章文本格式化"""
    if s is None:
        s = load_style_config()["ai"]
    text = escape_html(text)
    # 链接：棕色
    def replace_link(m):
        return f'<a href="{m.group(2)}" style="color:{s["accent"]};text-decoration:none">{m.group(1)}</a>'
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, text)
    # 粗体：加粗黑灰
    def replace_bold(m):
        return f'<b style="font-weight:bold;color:{s["bold"]}">{m.group(1)}</b>'
    text = re.sub(r'\*\*([^*]+)\*\*', replace_bold, text)
    # 代码：浅灰背景
    def replace_code(m):
        return f'<code style="font-size:13px;background:#f5f5f5;color:{s["accent"]};padding:2px 6px">{m.group(1)}</code>'
    text = re.sub(r'`([^`]+)`', replace_code, text)
    return text


def render_ai_table(rows, s):
    """渲染表格为微信兼容 HTML（AI文章风格）"""
    if not rows:
        return ""

    # 解析表头和内容行
    headers = [c.strip() for c in rows[0].split('|')[1:-1]]
    data_rows = []
    for row in rows[1:]:
        cells = [c.strip() for c in row.split('|')[1:-1]]
        if cells:
            data_rows.append(cells)

    base = 'padding:10px 12px;border:1px solid #ddd'
    html = '<table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:14px">\n'

    html += '  <thead>\n'
    html += '    <tr>\n'
    for h in headers:
        html += f'      <th style="{base};background:#f8f8f8;font-weight:bold;color:{s["bold"]};font-size:13px">{ai_format_text(h, s)}</th>\n'
    html += '    </tr>\n'
    html += '  </thead>\n'

    html += '  <tbody style="padding:10px 12px">\n'
    for i, row in enumerate(data_rows):
        bg = '#fff' if i % 2 == 0 else '#fafafa'
        html += '    <tr>\n'
        for cell in row:
            html += f'      <td style="{base};background:{bg}">{ai_format_text(cell, s)}</td>\n'
        html += '    </tr>\n'
    html += '  </tbody>\n'
    html += '</table>\n'

    return html


def render_ai_blockquote(text, s):
    """渲染引用块为微信兼容 HTML（AI文章风格）"""
    formatted = ai_format_text(escape_html(text.replace('\n', '<br>')), s)
    html = (
        f'<section style="margin:16px 0;padding:14px 16px;background:#f8f8f8'
        f';border-left:4px solid {s["accent"]}">'
        f'<p style="margin:0;font-size:14px;font-style:italic;color:#888;line-height:1.9">{formatted}</p>'
        f'</section>'
    )
    return html


def render_ai_code_block(code):
    """渲染代码块为微信兼容 HTML（AI文章风格，不依赖样式配置）"""
    if not code:
        return ""

    escaped = escape_html(code)
    lines = escaped.split('\n')
    html_lines = []
    for line in lines:
        line = re.sub(r'&lt;code&gt;([^&]+)&lt;/code&gt;', r'<code>\1</code>', line)
        html_lines.append(line)

    code_html = '<br>'.join(html_lines)

    html = f'''<section style="background:#f6f8fa;border:1px solid #e1e4e8;margin:16px 0;padding:16px;overflow-x:auto">
  <code style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:13px;color:#24292e;line-height:1.6;white-space:pre">{code_html}</code>
</section>'''
    return html


def render_ai_ending(s=None):
    """生成 AI 类文章尾部通用尾栏（微信兼容，极简内联样式）

    尾栏文字从样式配置 s 的 ending_lines 列表读取，可在 config.yaml 中覆盖。
    每个列表项渲染为一个 <p> 段落（支持内嵌 HTML 标签，如 <span style="...">）。
    """
    if s is None:
        s = load_style_config()["ai"]
    base_style = 'font-size:12px;color:#888;letter-spacing:0.5px;line-height:1.9'
    ending_lines = s.get("ending_lines", [
        "—End—",
        "如果觉得不错 随手点个 <span style=\"color:#ff4c41\">赞</span>、<span style=\"color:#ff2941\">在看</span>、<span style=\"color:#ff4c41\">转发</span> 三连吧",
        "<span style=\"color:#ff2941\">关注+星标</span> 可第一时间收到更多精彩思考和总结",
        "您的支持是我继续写下去的动力",
        "注：原创不易，合作请在公众号后台留言，未经许可，不得随意修改及盗用原文。",
    ])
    lines_html = ''.join(
        f'<p style="margin:0 0 10px 0">{line}</p>'
        for line in ending_lines
    )
    return (
        f'<section style="text-align:center;padding:24px 0 0 0;border-top:1px solid #eee;margin:20px 0 0 0;{base_style}">'
        f'{lines_html}'
        f'</section>'
    )


def generate_ai_html(data, s=None):
    """生成 AI 类公众号文章 HTML（白底灰字 + 棕色标签标题）"""
    if s is None:
        s = load_style_config()["ai"]

    content_parts = []
    for block in data["blocks"]:
        btype = block["type"]

        if btype == "heading":
            text = block["text"]
            level = block["level"]
            if level == 2:
                # H2：棕色居中标签标题（text-indent:0 从 body 继承，无需重复）
                content_parts.append(
                    f'<h2 style="margin:28px auto 18px;padding:8px 24px;font-size:{s["h2_font_size"]};font-weight:bold;color:#fff;'
                    f'background:{s["accent"]};text-align:center;display:block;'
                    f'width:fit-content;line-height:1.6;box-shadow:0 2px 6px rgba(0,0,0,0.12)">'
                    f'{ai_format_text(escape_html(text), s)}</h2>'
                )
            else:
                # H3：灰黑加粗标题
                content_parts.append(
                    f'<p style="margin:22px 0 12px 0;font-size:16px;font-weight:bold;color:#333;line-height:1.5">'
                    f'{ai_format_text(escape_html(text), s)}</p>'
                )
        elif btype == "table":
            content_parts.append(render_ai_table(block["rows"], s))
        elif btype == "blockquote":
            content_parts.append(render_ai_blockquote(block["text"], s))
        elif btype == "code_block":
            content_parts.append(render_ai_code_block(block["text"]))
        elif btype == "para":
            formatted = ai_format_text(escape_html(block["text"]), s)
            content_parts.append(
                f'<p style="margin:0 0 14px 0">{formatted}</p>'
            )

    content = '\n'.join(content_parts)

    # 尾栏
    ending = render_ai_ending(s)

    # 替换模板占位符
    html = AI_HTML_TEMPLATE.format(
        ai_bg=s["bg"],
        ai_text=s["text"],
        ai_tag_bg=s["tag_bg"],
        ai_tag_txt=s["tag_txt"],
        title=escape_html(data["title"]),
        content=content,
        cover_label=s.get("cover_label", "AI 实践观察"),
        title_font_size=s["title_font_size"],
        text_font_size=s["text_font_size"],
    )
    # 尾栏追加到正文末尾
    html = html.replace('</section>\n\n</body>', f'</section>\n{ending}\n\n</body>')
    return html


# ─── 主入口 ─────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    mode = "daily"  # daily | essay | ai
    config_path = None

    i = 0
    while i < len(args):
        if args[i] == '--essay':
            mode = "essay"
        elif args[i] == '--ai':
            mode = "ai"
        elif args[i] == '--config':
            i += 1
            if i < len(args):
                config_path = args[i]
        else:
            break
        i += 1
    args = args[i:]

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

    # 加载样式配置
    style_cfg = load_style_config(config_path=config_path)

    if mode == "essay":
        data = parse_essay(md_text)
        html = generate_essay_html(data, s=style_cfg["essay"])
        print(f"生成成功（长文模式）: {output_file}")
        print(f"   标题: {data['title']}")
        print(f"   段落块数: {len(data['blocks'])}")
    elif mode == "ai":
        data = parse_essay(md_text)
        html = generate_ai_html(data, s=style_cfg["ai"])
        print(f"生成成功（AI文章模式）: {output_file}")
        print(f"   标题: {data['title']}")
        print(f"   段落块数: {len(data['blocks'])}")
    else:
        data = parse_markdown(md_text)
        html = generate_wechat_html(data, s=style_cfg["daily"])
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
