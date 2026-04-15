#!/usr/bin/env python3
from __future__ import annotations

import sys
import re
from pathlib import Path
from typing import Iterable, Optional

try:
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md
except ImportError as exc:
    print('[ERROR] HTML parser dependencies are missing: beautifulsoup4, markdownify', file=sys.stderr)
    raise SystemExit(1) from exc

CONTENT_KEYWORDS = (
    '사업개요', '지원대상', '신청기간', '문의처', '접수기간', '지원분야',
    '사업안내', '사업신청', '주관기관', '사업수행기관', '지원예산', '규모',
    '지원내용', '모집공고', '모집대상', '공고개요', '운영목적', '신청방법',
    '접수방법', '첨부파일', '상세내용',
)
UI_KEYWORDS = (
    '로그인', '회원가입', '전체메뉴', '사이트맵', '본문 바로가기', '검색어를 입력하세요',
    '현재페이지의 내용과 사용편의성에 만족하십니까', '글자크게', '글자작게',
    '페이스북으로 공유', '카카오톡 공유', '페이지 상단으로 이동', '페이지 하단으로 이동',
    '후원', '기부금영수증', '나의 후원내역 보기',
)
SELECTORS = (
    '#contentViewHtml',
    '.support_view',
    '.cont_body',
    '.s_view',
    '.projectCate',
    '.article-content',
    '.article-cont',
    'article.post',
    '.post',
    '.view_cont_wrap',
    '.view_cont',
    '.support_project_detail',
    '.board_detail',
    '.board_wrap',
    '.sub_cont',
    '#content',
    '.content_wrap',
    'main',
    'article',
    '.content',
    '.contents',
    '#container',
    'body',
)
SELECTOR_SCORES = {
    '#contentViewHtml': 600,
    '.support_view': 500,
    '.cont_body': 450,
    '.s_view': 450,
    '.projectCate': 420,
    '.article-content': 420,
    '.article-cont': 400,
    'article.post': 380,
    '.post': 320,
    '.view_cont_wrap': 360,
    '.view_cont': 360,
    '.support_project_detail': 340,
    '.board_detail': 320,
    '.board_wrap': 280,
    '.sub_cont': 260,
    '#content': 260,
    '.content_wrap': 160,
    'main': 80,
    'article': 60,
    '.content': 0,
    '.contents': 0,
    '#container': -120,
    'body': -300,
}
REMOVE_SELECTORS = (
    'script', 'style', 'noscript', 'svg', 'iframe', 'form', 'header', 'footer', 'nav', 'aside',
    '.header', '.footer', '.gnb', '.lnb', '.snb', '.all_menu', '.social', '.social_inner', '.copy_right_wrap',
    '.search-wrap', '.search_top', '.search_box', '.search', '.navi_wrap', '.location', '.breadcrumb', '.navi',
    '.btn_area', '.board_btn', '.view_list_go', '.popup_wrap', '.modal', '.family_site', '.skip', '.blind',
    '.tag_list', '.hashtags_modal', '.btn_area2', '.satisfaction', '.recommend_project', '.other_list',
    '.similar_announcement',
    '.view_list', '.view_list_wrap', '.social_list-wrap',
    '.share', '.share_wrap', '.sns', '.skip-link', '.mega-menu-wrap', '#mega-menu-wrap-gnb',
    '.donation-info', '.header_wrap', '.top_banner', '.quick_menu', '.utility', '.allmenu',
)


def clean_node(node) -> None:
    for selector in REMOVE_SELECTORS:
        for tag in list(node.select(selector)):
            tag.decompose()
    for tag in list(node.find_all(attrs={'hidden': True})):
        tag.decompose()
    for tag in list(node.find_all(style=True)):
        if getattr(tag, 'attrs', None) is None:
            continue
        style = (tag.get('style') or '').replace(' ', '').lower()
        if 'display:none' in style:
            tag.decompose()


def normalized_text(text: str) -> str:
    return ' '.join(text.split())


def candidate_score(node, selector: str) -> tuple[int, str]:
    text = node.get_text('\n', strip=True)
    normalized = normalized_text(text)
    score = len(normalized)
    for keyword in CONTENT_KEYWORDS:
        if keyword in normalized:
            score += 300
    for keyword in UI_KEYWORDS:
        if keyword in normalized:
            score -= 180
    score += SELECTOR_SCORES.get(selector, 0)
    link_count = len(node.find_all('a'))
    score -= min(link_count * 12, 360)
    line_count = len([line for line in text.splitlines() if line.strip()])
    if line_count < 4:
        score -= 150
    return score, text


def best_node(soup: BeautifulSoup):
    best = None
    best_score = -1
    for selector in SELECTORS:
        for node in soup.select(selector):
            clone = BeautifulSoup(str(node), 'lxml')
            candidate = clone.select_one(selector) if selector != 'body' else clone.body
            if candidate is None:
                candidate = clone
            clean_node(candidate)
            score, text = candidate_score(candidate, selector)
            if score > best_score and len(text) >= 120:
                best_score = score
                best = candidate
    return best


def iter_candidate_soups(html: str) -> list[BeautifulSoup]:
    fragments = [html]
    html_indexes = [match.start() for match in re.finditer(r"<html", html, re.I)]
    for idx in html_indexes[1:]:
        fragments.append(html[idx:])
    for pattern in [
        r'<section[^>]+id="container"',
        r'<div[^>]+class="[^"]*sub_cont',
        r'<div[^>]+class="[^"]*view_cont',
        r'<div[^>]+class="[^"]*support_view',
        r'<article[^>]+class="[^"]*post',
    ]:
        for match in re.finditer(pattern, html, re.I):
            fragments.append(html[match.start():])
    soups: list[BeautifulSoup] = []
    seen: set[str] = set()
    for fragment in fragments:
        if fragment in seen:
            continue
        seen.add(fragment)
        soups.append(BeautifulSoup(fragment, "lxml"))
    return soups


def best_node_from_html(html: str):
    best = None
    best_score = -1
    for soup in iter_candidate_soups(html):
        candidate = best_node(soup)
        if candidate is None:
            continue
        score, _ = candidate_score(candidate, "body")
        if score > best_score:
            best = candidate
            best_score = score
    return best


def meta_content(soup: BeautifulSoup, selectors: Iterable[tuple[str, Optional[str]]]) -> str:
    for selector, attr in selectors:
        node = soup.select_one(selector)
        if not node:
            continue
        value = node.get(attr) if attr else node.get_text(' ', strip=True)
        if value and value.strip():
            return normalized_text(value)
    return ''


def title_from(soup: BeautifulSoup) -> str:
    return meta_content(soup, [
        ('meta[property="og:title"]', 'content'),
        ('meta[name="title"]', 'content'),
        ('title', None),
        ('h1', None),
        ('h2.title', None),
        ('h3', None),
    ])


def fallback_markdown(soup: BeautifulSoup, title: str) -> str:
    description = meta_content(soup, [
        ('meta[property="og:description"]', 'content'),
        ('meta[name="description"]', 'content'),
        ('meta[name="twitter:description"]', 'content'),
    ])
    body_text = normalized_text((soup.body or soup).get_text(' ', strip=True))
    hints = []
    if soup.select_one('#app, #root, #__next, #nsv_root'):
        hints.append('이 페이지는 정적 HTML만으로는 본문이 보이지 않는 동적 앱 셸로 보입니다.')
    if "doesn't work properly without javascript enabled" in body_text.lower():
        hints.append('JavaScript 활성화가 필요한 페이지라는 문구만 확인되었습니다.')
    if not description and body_text:
        description = body_text[:280]

    parts = []
    if title:
        parts.append(f'# {title}')
        parts.append('')
    if description:
        parts.append(description)
    if hints:
        if parts and parts[-1] != '':
            parts.append('')
        parts.extend(f'- {hint}' for hint in hints)
    if not parts:
        parts.append("TODO: 정적 HTML에서 의미 있는 본문을 추출하지 못했습니다.")
    return '\n'.join(parts).strip()


def main(src: str, out: str) -> int:
    html = Path(src).read_text(encoding='utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'lxml')
    title = title_from(soup)
    node = best_node_from_html(html)
    if node is None:
        node = soup.body or soup
        clean_node(node)
    markdown = md(
        str(node),
        heading_style='ATX',
        bullets='-',
        strip=['img'],
    ).strip()
    if not markdown:
        markdown = fallback_markdown(soup, title)
    markdown = '\n'.join(line.rstrip() for line in markdown.splitlines())
    markdown = '\n'.join(line for line in markdown.splitlines() if line.strip() or (line == '' and markdown))
    parts = []
    if title and not markdown.startswith(f'# {title}'):
        parts.append(f'# {title}')
        parts.append('')
    parts.append(markdown)
    result = '\n'.join(parts).strip() + '\n'
    Path(out).write_text(result, encoding='utf-8')
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: parse-html.py <src.html> <out.md>', file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
