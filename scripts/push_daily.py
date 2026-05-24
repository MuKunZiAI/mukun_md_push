#!/usr/bin/env python3
"""
日报/长文推送脚本：Markdown → 微信兼容 HTML → 草稿箱

用法:
  # 日报模式（默认）
  python3 push_daily.py <input.md> [--title TITLE] [--cover COVER_IMAGE] [--digest DIGEST] [--media-id MEDIA_ID]

  # 长文/成语故事模式
  python3 push_daily.py --essay <input.md> [--title TITLE] [--cover COVER_IMAGE] [--digest DIGEST] [--media-id MEDIA_ID]

  # AI类文章模式
  python3 push_daily.py --ai <input.md> [--title TITLE] [--cover COVER_IMAGE] [--digest DIGEST] [--media-id MEDIA_ID]

Markdown frontmatter 支持（在文件顶部加 YAML 区段，可省去 --title 和 --digest 参数）：
  ---
  title: 文章标题
  digest: 手动摘要（80字以内）
  ---
  # 文章标题（仍是必填）

封面图处理:
- media_id 获取优先级：命令行 --media-id > config.yaml wechat.media_id > 上传封面图
- 日报模式：首次上传封面图，media_id 保存到 cover_media_id.txt，后续复用
- 长文模式（--essay）：每个成语封面图都是专属的，每次都重新上传，不复用
- AI文章模式（--ai）：每篇文章封面图不同，每次都重新上传，不复用
- 默认封面图: 当前目录下的 "封面图.png"
- --essay 模式默认使用 "成语历史典故封面.png"（如存在）
- --ai 模式默认使用 "AI文章封面.png"（如存在）
- 1:1 裁剪坐标固定为 "1008,0,1872,864"（成语典故系列）

完整工作流:
  1. Markdown → 微信兼容 HTML (md2wechat_html.py，--essay 模式时加 --essay 参数)
  2. 上传封面图（首次）
  3. 推送草稿箱
"""

import json
import os
import re
import ssl
import sys
import subprocess
import urllib.request

# ─── 配置 ───────────────────────────────────────────────


CONFIG_PATH = os.path.join(os.path.expanduser("~/.md_push_wechat"), "config.yaml")
API_BASE = "https://api.weixin.qq.com"
COVER_MEDIA_ID_FILE = os.path.join(os.path.expanduser("~/.md_push_wechat"), "cover_media_id.txt")
ESSAY_COVER_MEDIA_ID_FILE = os.path.join(os.path.expanduser("~/.md_push_wechat"), "essay_cover_media_id.txt")
AI_COVER_MEDIA_ID_FILE = os.path.join(os.path.expanduser("~/.md_push_wechat"), "ai_cover_media_id.txt")
DEFAULT_COVER = os.path.join(os.path.expanduser("~/.md_push_wechat"), "封面图.png")
DEFAULT_ESSAY_COVER = os.path.join(os.path.expanduser("~/.md_push_wechat"), "成语历史典故封面.png")
DEFAULT_AI_COVER = os.path.join(os.path.expanduser("~/.md_push_wechat"), "AI文章封面.png")
MD2WECHAT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "md2wechat_html.py")

# ─── 工具函数 ───────────────────────────────────────────

def load_credentials():
    """从 config.yaml 读取 wechat.appid 和 wechat.secret"""
    if not os.path.exists(CONFIG_PATH):
        print(f"ERROR: 配置文件不存在: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    appid_match = re.search(r"appid:\s+(\S+)", content)
    secret_match = re.search(r"secret:\s+(\S+)", content)
    if not appid_match or not secret_match:
        print("ERROR: 无法从配置文件中读取 appid/secret")
        sys.exit(1)
    return appid_match.group(1).strip(), secret_match.group(1).strip()


def load_config_media_id():
    """从 config.yaml 读取 wechat.media_id（封面图的永久素材 ID）"""
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"media_id:\s*(\S+)", content)
    return match.group(1).strip() if match else None


def get_access_token(appid, secret):
    """获取微信 access_token"""
    ctx = ssl.create_default_context()
    url = f"{API_BASE}/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}"
    with urllib.request.urlopen(url, context=ctx) as resp:
        data = json.loads(resp.read())
    if "access_token" not in data:
        print(f"ERROR: 获取 access_token 失败: {json.dumps(data, ensure_ascii=False)}")
        sys.exit(1)
    return data["access_token"]


def upload_image(access_token, image_path):
    """上传图片到永久素材库，返回 media_id"""
    ctx = ssl.create_default_context()
    filename = os.path.basename(image_path)
    with open(image_path, "rb") as f:
        file_data = f.read()
    
    boundary = "----WechatDraftBoundary7MA4YWxkTrZu0gW"
    body_parts = []
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n".encode("utf-8")
    )
    body_parts.append(file_data)
    body_parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(body_parts)
    
    url = f"{API_BASE}/cgi-bin/material/add_material?access_token={access_token}&type=image"
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req, context=ctx) as resp:
        result = json.loads(resp.read())
    
    if "media_id" not in result:
        print(f"ERROR: 封面图上传失败: {json.dumps(result, ensure_ascii=False)}")
        sys.exit(1)
    
    return result["media_id"]


def get_cover_media_id(access_token, cover_path, essay_mode=False, ai_mode=False, cmd_media_id=None):
    """获取封面图 media_id

    优先级：命令行 --media-id > config.yaml wechat.media_id > 上传封面图
    日报模式：复用已保存的 media_id（同一张封面图）
    成语模式（essay_mode=True）：每次都上传新封面（每个成语封面图不同）
    AI文章模式（ai_mode=True）：每次都上传新封面（每个AI文章封面图不同）
    """
    # 1. 命令行指定的 media_id 优先级最高
    if cmd_media_id:
        print(f"使用命令行指定的 media_id: {cmd_media_id}")
        return cmd_media_id

    # 2. config.yaml 中配置的 media_id
    config_media_id = load_config_media_id()
    if config_media_id:
        print(f"使用 config.yaml 配置的 media_id: {config_media_id}")
        return config_media_id

    # 3. AI模式/成语模式：每次都上传新封面图（不复用）
    cache_file = AI_COVER_MEDIA_ID_FILE if ai_mode else (ESSAY_COVER_MEDIA_ID_FILE if essay_mode else COVER_MEDIA_ID_FILE)

    if ai_mode or essay_mode:
        if not os.path.exists(cover_path):
            print(f"ERROR: 封面图不存在: {cover_path}")
            sys.exit(1)
        print(f"上传封面图: {cover_path}")
        media_id = upload_image(access_token, cover_path)
        print(f"封面图 media_id: {media_id}")
        return media_id

    # 日报模式：检查是否有已保存的 media_id
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            saved = f.read().strip()
        if saved:
            print(f"复用已保存的封面图 media_id: {saved}")
            return saved
    
    # 上传新封面图
    if not os.path.exists(cover_path):
        print(f"ERROR: 封面图不存在: {cover_path}")
        print("提示: 在当前目录下放一张名为 '封面图.png' 的图片，或用 --cover 指定路径")
        sys.exit(1)
    
    print(f"上传封面图: {cover_path}")
    media_id = upload_image(access_token, cover_path)
    
    # 保存 media_id
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(media_id)
    print(f"封面图 media_id 已保存到: {cache_file}")
    
    return media_id


# 硬编码的 1:1 裁剪坐标（用于成语典故系列封面）
# 封面图尺寸 2016×864，1:1 裁剪取中心竖条
# 格式：X1_Y1_X2_Y2（归一化坐标，0~1，下划线分隔）
# 计算：X1=1008/2016=0.5，Y1=0，X2=1872/2016≈0.928571，Y2=864/864=1
HARDCODED_PIC_CROP_1_1 = "0.5_0_0.928571_1"


MAX_CONTENT_LENGTH = 20000  # 微信草稿接口单篇字符限制
MAX_TITLE_LENGTH = 64  # 微信图文标题限制（草稿接口实际支持 64 字符）


def _truncate_title(title, max_len=MAX_TITLE_LENGTH):
    """截断标题到指定长度，保留后缀

    当标题含后缀（如「...（上）」「...（下）」）时，截断原文部分确保后缀不丢失。
    无后缀时直接截断。
    """
    if len(title) <= max_len:
        return title

    # 检测常见中文后缀：全角括号（上）（中）（下）（续）或（N）
    suffix_match = re.search(r'（[^）]*）\s*$', title)
    if suffix_match:
        suffix = suffix_match.group(0)
        available = max_len - len(suffix)
        if available > 4:  # 至少留 4 个字
            return title[:available] + suffix

    return title[:max_len]


def split_html_content(html_content, title):
    """将超限的 HTML 内容按 H2 标签拆分为多篇

    拆分策略：
    1. 提取 body style、封面 section、正文 section 外层标签
    2. 在正文 section 内按 H2 切割
    3. 按字符预算分组合并，每篇保留封面 + 正文片段
    4. 首篇保留原始标题，后续篇加 (上/中/下) 后缀
    5. 尾栏 section 只出现在最后一篇

    返回: [(part_title, part_html), ...]
    """
    # 1. 提取 body style
    body_style_match = re.search(r'<body\s+style="([^"]+)"', html_content)
    body_style = body_style_match.group(1) if body_style_match else ""

    # 2. 提取封面 section（从 <!-- 封面 --> 注释到下一个顶层 section 之前）
    cover_match = re.search(
        r'(<!-- 封面 -->.*?</section>)',
        html_content, re.DOTALL
    )
    cover_html = cover_match.group(1) if cover_match else ""

    # 3. 提取正文 section 的开标签（含 style）
    #    正文中还有代码块、引用块等子 section，需要精确匹配
    content_open_match = re.search(
        r'(<!-- 正文区域[^\n]*\n\s*-->\s*)(<section\s+style="[^"]+">)',
        html_content
    )
    if content_open_match:
        comment_part = content_open_match.group(1)
        content_section_open = content_open_match.group(2)
    else:
        # 回退：找 body 后第一个带 font-size/line-height 的 section
        fallback = re.search(
            r'(<section\s+style="[^"]*font-size[^"]*">)',
            html_content
        )
        comment_part = ""
        content_section_open = fallback.group(1) if fallback else '<section>'

    # 4. 提取尾栏 section（AI 模式的固定尾栏，最后一篇才保留）
    tail_match = re.search(
        r'(<section\s+style="[^"]*text-align:center[^"]*">.*?</section>\s*</body>)',
        html_content, re.DOTALL
    )
    tail_html = tail_match.group(1) if tail_match else ""

    # 5. 提取正文 section 内的内容（去掉外层标签）
    body_match = re.search(r'<body[^>]*>(.*)</body>', html_content, re.DOTALL)
    if not body_match:
        return [(title, html_content)]
    body_inner = body_match.group(1)

    # 找到正文 section 的开始位置
    if content_open_match:
        # 正文内容从 content_section_open 之后开始
        content_start = content_open_match.end()
    else:
        content_start = len(cover_html) + 10  # 估算

    # 提取正文内容（从正文 section 开始到尾栏之前）
    if tail_match:
        # 从 body_inner 中找到尾栏的位置
        tail_in_body = body_inner.find(tail_html.split("</body>")[0].strip())
        if tail_in_body > 0:
            content_area = body_inner[content_start:tail_in_body]
        else:
            content_area = body_inner[content_start:]
    else:
        content_area = body_inner[content_start:]

    # 6. 按 H2 拆分
    h2_pattern = re.compile(r'(<h2\s+style="[^"]+">)(.*?)(</h2>)', re.DOTALL)
    h2_positions = []
    for m in h2_pattern.finditer(content_area):
        # 只匹配顶层 H2（不在子 section 内的）
        # 简单启发：检查 H2 前面的 section 嵌套深度
        prefix = content_area[:m.start()]
        open_sections = prefix.count('<section')
        close_sections = prefix.count('</section')
        if open_sections - close_sections <= 1:  # 顶层
            h2_positions.append((m.start(), m.end(), m.group(2).strip()))

    if len(h2_positions) < 2:
        return [(title, html_content)]

    # 7. 切分为 H2 块
    chunks = []
    for idx, (start, end, h2_text) in enumerate(h2_positions):
        if idx + 1 < len(h2_positions):
            chunk = content_area[start:h2_positions[idx + 1][0]]
        else:
            chunk = content_area[start:]
        chunks.append((h2_text, chunk))

    # 8. 分组合并（每篇不超过 MAX_CONTENT_LENGTH）
    # 模板开销估算
    template_head = f'<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="{body_style}">\n'
    template_foot = '\n</body>\n</html>'
    per_article_overhead = len(template_head) + len(cover_html) + len(comment_part) + len(content_section_open) + len("</section>") + len(template_foot) + 100

    articles_content = []  # 每篇的正文块列表
    current_chunks = []
    current_len = 0

    for h2_text, chunk in chunks:
        chunk_len = len(chunk)
        if current_chunks and current_len + chunk_len > MAX_CONTENT_LENGTH - per_article_overhead:
            articles_content.append(current_chunks)
            current_chunks = []
            current_len = 0
        current_chunks.append(chunk)
        current_len += chunk_len

    if current_chunks:
        articles_content.append(current_chunks)

    if len(articles_content) == 1:
        return [(title, html_content)]

    # 9. 构建每篇完整 HTML
    parts = []
    n = len(articles_content)

    # 根据篇数选择后缀列表
    if n == 2:
        suffixes = ["（上）", "（下）"]
    elif n == 3:
        suffixes = ["（上）", "（中）", "（下）"]
    else:
        suffixes = [f"（{i+1}）" for i in range(n)]
        suffixes[-1] = "（续）"

    for i, chunk_list in enumerate(articles_content):
        merged_content = "".join(chunk_list)

        part_title = title + " " + suffixes[i]

        # 尾栏只加在最后一篇
        part_tail = tail_html if i == len(articles_content) - 1 else ""

        part_html = (
            f'{template_head}'
            f'{cover_html}\n'
            f'{comment_part}{content_section_open}'
            f'{merged_content}'
            f'</section>\n'
            f'{part_tail}'
            f'{template_foot}'
        )

        # 安全检查
        if len(part_html) > MAX_CONTENT_LENGTH:
            print(f"WARNING: 第 {i+1} 篇仍超限 ({len(part_html)} 字符)，截断处理")
            # 尝试去掉封面来省空间（非首篇）
            if i > 0:
                part_html = part_html.replace(cover_html + "\n", "")
            if len(part_html) > MAX_CONTENT_LENGTH:
                part_html = part_html[:MAX_CONTENT_LENGTH]

        parts.append((part_title, part_html))

    return parts


def push_draft(access_token, title, html_content, thumb_media_id, cover_path="", digest=""):
    """推送草稿箱（自动拆分超限内容为多篇合并推送）"""
    if len(html_content) > MAX_CONTENT_LENGTH:
        print(f"内容 {len(html_content)} 字符超过限制 {MAX_CONTENT_LENGTH}，自动拆分为多篇合并推送")
        parts = split_html_content(html_content, title)
        print(f"拆分为 {len(parts)} 篇:")
        for i, (pt, ph) in enumerate(parts):
            print(f"  第 {i+1} 篇: {pt} ({len(ph)} 字符)")
        return _push_multi_drafts(access_token, parts, thumb_media_id, cover_path, digest)

    return _push_single_draft(access_token, title, html_content, thumb_media_id, cover_path, digest)


def _make_article(title, html_content, thumb_media_id, digest="", pic_crop_1_1=""):
    """构建单篇图文消息结构"""
    article = {
        "article_type": "news",
        "title": title,
        "content": html_content,
        "thumb_media_id": thumb_media_id,
        "author": "木昆子",
        "need_open_comment": 1,
        "only_fans_can_comment": 1,
    }
    if digest:
        article["digest"] = digest
    if pic_crop_1_1:
        article["pic_crop_1_1"] = pic_crop_1_1
    return article


def _push_single_draft(access_token, title, html_content, thumb_media_id, cover_path="", digest=""):
    """推送单篇草稿"""
    # 生成摘要
    if not digest:
        plain_text = re.sub(r"<[^>]+>", "", html_content)
        plain_text = re.sub(r"\s+", " ", plain_text).strip()
        digest = plain_text[:120] if len(plain_text) > 120 else plain_text

    title = _truncate_title(title)
    print(f"标题: {title}")
    print(f"摘要: {digest[:50]}{'...' if len(digest) > 50 else ''}")
    print(f"内容长度: {len(html_content)} 字符")

    pic_crop_1_1 = HARDCODED_PIC_CROP_1_1 if cover_path else ""
    if pic_crop_1_1:
        print(f"封面图 1:1 裁剪坐标: {pic_crop_1_1}")

    article = _make_article(title, html_content, thumb_media_id, digest, pic_crop_1_1)
    payload = {"articles": [article]}

    ctx = ssl.create_default_context()
    url = f"{API_BASE}/cgi-bin/draft/add?access_token={access_token}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    with urllib.request.urlopen(req, context=ctx) as resp:
        result = json.loads(resp.read())

    if result.get("errcode") and result["errcode"] != 0:
        print(f"ERROR: 推送失败: {json.dumps(result, ensure_ascii=False)}")
        sys.exit(1)

    media_id = result.get("media_id", "")
    print(f"✅ 推送成功! media_id: {media_id}")
    return media_id


def _push_multi_drafts(access_token, parts, thumb_media_id, cover_path="", digest=""):
    """推送多篇合并为一个图文消息（自动拆分后调用）"""
    pic_crop_1_1 = HARDCODED_PIC_CROP_1_1 if cover_path else ""

    articles = []
    for i, (part_title, part_html) in enumerate(parts):
        part_digest = digest or ""

        part_title = _truncate_title(part_title)

        article = _make_article(part_title, part_html, thumb_media_id, part_digest, pic_crop_1_1)
        articles.append(article)
        print(f"  第 {i+1} 篇: 「{part_title}」({len(part_html)} 字符)")

    payload = {"articles": articles}

    ctx = ssl.create_default_context()
    url = f"{API_BASE}/cgi-bin/draft/add?access_token={access_token}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    with urllib.request.urlopen(req, context=ctx) as resp:
        result = json.loads(resp.read())

    if result.get("errcode") and result["errcode"] != 0:
        print(f"ERROR: 推送失败: {json.dumps(result, ensure_ascii=False)}")
        sys.exit(1)

    media_id = result.get("media_id", "")
    print(f"✅ 合并推送成功! {len(articles)} 篇, media_id: {media_id}")
    return media_id


def extract_frontmatter(md_file):
    """从 Markdown 文件提取 frontmatter 元数据（标题、摘要等）

    支持 YAML frontmatter 格式：
    ---
    title: 标题
    digest: 摘要（可选，80字以内）
    ---
    """
    with open(md_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 解析 YAML frontmatter（纯字符串解析，不依赖 yaml 模块）
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter_block = parts[1]
            title = ""
            digest = ""
            for line in frontmatter_block.splitlines():
                line = line.strip()
                if line.startswith("title:"):
                    title = line[6:].strip().strip("\"'")
                elif line.startswith("digest:"):
                    digest = line[7:].strip().strip("\"'")
            if title:
                return title, digest

    # 回退：直接从 # 标题行提取
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip(), ""
    return "未命名日报", ""


# ─── 主入口 ─────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    args = sys.argv[1:]
    essay_mode = False
    ai_mode = False

    # 识别 --essay 或 --ai 参数（位置不限，但必须在 md 文件之前或之后均可）
    if "--ai" in args:
        ai_mode = True
        args = [a for a in args if a != "--ai"]
    if "--essay" in args:
        essay_mode = True
        args = [a for a in args if a != "--essay"]

    if not args:
        print(__doc__.strip())
        sys.exit(1)

    md_file = args[0]
    title = None
    digest = None  # 手动指定的摘要
    cover = None   # 延迟到确定 essay_mode 后再设默认值
    media_id = None  # 手动指定的封面 media_id

    i = 1
    while i < len(args):
        if args[i] == "--title" and i + 1 < len(args):
            title = args[i + 1]
            i += 2
        elif args[i] == "--cover" and i + 1 < len(args):
            cover = args[i + 1]
            i += 2
        elif args[i] == "--digest" and i + 1 < len(args):
            digest = args[i + 1]
            i += 2
        elif args[i] == "--media-id" and i + 1 < len(args):
            media_id = args[i + 1]
            i += 2
        else:
            i += 1

    # 根据模式设定默认封面图
    if cover is None:
        if ai_mode and os.path.exists(DEFAULT_AI_COVER):
            cover = DEFAULT_AI_COVER
        elif essay_mode and os.path.exists(DEFAULT_ESSAY_COVER):
            cover = DEFAULT_ESSAY_COVER
        else:
            cover = DEFAULT_COVER

    if not os.path.exists(md_file):
        print(f"ERROR: Markdown 文件不存在: {md_file}")
        sys.exit(1)

    # 1. 生成微信兼容 HTML
    base = os.path.splitext(md_file)[0]
    if ai_mode:
        html_file = f"{base}_ai_wechat.html"
        mode_label = "AI文章模式"
        cmd = [sys.executable, MD2WECHAT_SCRIPT, "--ai", md_file, html_file]
    elif essay_mode:
        html_file = f"{base}_essay_wechat.html"
        mode_label = "长文/成语模式"
        cmd = [sys.executable, MD2WECHAT_SCRIPT, "--essay", md_file, html_file]
    else:
        html_file = f"{base}_wechat.html"
        mode_label = "日报模式"
        cmd = [sys.executable, MD2WECHAT_SCRIPT, md_file, html_file]

    print(f"步骤 1: Markdown → 微信兼容 HTML（{mode_label}）")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: HTML 生成失败:\n{result.stderr}")
        sys.exit(1)
    print(result.stdout.strip())

    # 读取 HTML 内容
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. 获取标题和摘要（优先 frontmatter > 命令行参数 > 自动截取）
    frontmatter_title, frontmatter_digest = extract_frontmatter(md_file)
    if not title:
        title = frontmatter_title
        title = _truncate_title(title)
    if not digest:
        digest = frontmatter_digest
    if digest:
        print(f"摘要（frontmatter）: {digest}")

    # 3. 获取凭证并上传封面图
    print(f"\n步骤 2: 获取凭证并处理封面图")
    appid, secret = load_credentials()
    token = get_access_token(appid, secret)
    thumb_media_id = get_cover_media_id(token, cover, essay_mode=essay_mode, ai_mode=ai_mode, cmd_media_id=media_id)

    # 4. 推送草稿箱
    print(f"\n步骤 3: 推送草稿箱")
    media_id = push_draft(token, title, html_content, thumb_media_id, cover_path=cover, digest=digest)

    print(f"\n完成! 草稿 media_id: {media_id}")


if __name__ == "__main__":
    main()
