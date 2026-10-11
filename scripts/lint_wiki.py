#!/usr/bin/env python3
"""Portable wiki metadata, source and local-link checks (no graph or LLM)."""
from __future__ import annotations
import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
try:
    import yaml
except ImportError:
    raise SystemExit('PyYAML가 필요합니다: python -m pip install -r scripts/requirements-core.txt')
ROOT = Path(__file__).resolve().parents[1]

# Reject duplicate metadata keys instead of silently taking the last value.
class UniqueLoader(yaml.SafeLoader):
    pass

def mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f'duplicate key: {key}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result
UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)

def is_date(value):
    try:
        date.fromisoformat(str(value))
        return True
    except ValueError:
        return False

def external(value):
    return bool(urlsplit(value).scheme) or value.startswith('//')

def local_target(root, document, target, source=False, wiki=False):
    target = unquote(target.split('#', 1)[0].split('?', 1)[0]).strip('<>')
    if not target: return True
    if target.startswith('/'):
        candidates = [root / target.lstrip('/')]
    elif source:
        candidates = [root / target]
    else:
        candidates = [document.parent / target]
        if wiki: candidates += [root / target, root / 'wiki' / target]
    if wiki:
        candidates += [p.with_suffix('.md') for p in candidates if not p.suffix]
        if '/' not in target:
            candidates += list((root / 'wiki').rglob(target if target.endswith('.md') else target + '.md'))
    return any(p.resolve().is_relative_to(root.resolve()) and p.exists() for p in candidates)

def run_lint(root=ROOT, scopes=None):
    root = Path(root).resolve()
    errors = []
    files = set()
    for scope in scopes or ['wiki']:
        p = root / scope
        if not p.resolve().is_relative_to(root):
            errors.append({'file': str(scope), 'item': 'scope', 'detail': '저장소 밖 경로'})
            continue
        if not p.exists():
            errors.append({'file': str(scope), 'item': 'scope', 'detail': '경로 없음'})
            continue
        files.update([p] if p.is_file() else p.rglob('*.md'))
    for f in sorted(files):
        rel = f.relative_to(root).as_posix()
        def add(item, detail): errors.append({'file': rel, 'item': item, 'detail': detail})
        if not f.resolve().is_relative_to(root):
            add('scope', '저장소 밖 파일'); continue
        try: text = f.read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            add('read', '문서 읽기 실패'); continue
        match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
        if not match:
            add('frontmatter', 'YAML frontmatter 없음'); continue
        try:
            meta = yaml.load(match.group(1), Loader=UniqueLoader)
            if not isinstance(meta, dict): raise ValueError('mapping required')
        except (yaml.YAMLError, ValueError, TypeError):
            add('frontmatter', '잘못된 YAML 또는 중복 키'); continue
        for key in ['title', 'owner', 'status', 'updated', 'tags', 'source']:
            if key not in meta: add('required', key)
        for key in ['title', 'owner']:
            if not isinstance(meta.get(key), str) or not meta[key].strip(): add('field', key+'는 비어 있지 않은 문자열이어야 함')
        if meta.get('status') not in ['draft','published','archived']: add('field','status 값 오류')
        if not is_date(meta.get('updated')): add('field','updated 날짜 오류')
        for key in ['tags','source']:
            if not isinstance(meta.get(key), list) or any(not isinstance(x,str) for x in meta.get(key, [])):
                add('field',key+'는 문자열 목록이어야 함')
        if meta.get('confidence') not in [None,'high','medium','low','unverified']: add('field','confidence 값 오류')
        for key in ['verified','disputed']:
            if key in meta and not isinstance(meta[key], bool): add('field',key+'는 boolean이어야 함')
        if meta.get('verified') is True:
            if not isinstance(meta.get('verified_by'),str) or not meta['verified_by'].strip(): add('verified','verified_by 없음')
            if not is_date(meta.get('verified_at')): add('verified','verified_at 날짜 없음 또는 오류')
        for source in meta.get('source',[]) if isinstance(meta.get('source'),list) else []:
            if isinstance(source,str) and (not source.strip() or (not external(source) and not local_target(root,f,source,source=True))): add('source',source)
        body = re.sub(r'<!--.*?-->', '', text[match.end():], flags=re.S)
        body = re.sub(r'^\s*(`{3,}|~{3,}).*?^\s*\1\s*$', '', body, flags=re.M|re.S)
        body = re.sub(r'`[^`\n]*`','',body)
        for target in re.findall(r'!?\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)',body):
            target = target.strip('<>')
            if not external(target) and not local_target(root,f,target): add('link',target)
        for target in re.findall(r'\[\[([^\]\n]+)\]\]',body):
            target=target.split('|',1)[0]
            if not local_target(root,f,target,wiki=True): add('wikilink',target)
        # Reference-style links: validate definitions and undefined references.
        refs = {k.casefold(): v.strip('<>') for k,v in re.findall(r'^\s*\[([^\]]+)\]:\s*(<[^>]+>|\S+)',body,re.M)}
        for key,target in refs.items():
            if not external(target) and not local_target(root,f,target): add('link',target)
        for label,key in re.findall(r'(?<!!)\[([^\]\n]+)\]\[([^\]\n]*)\]',body):
            if (key or label).casefold() not in refs: add('link','정의 없는 참조: '+(key or label))
    return {'files':len(files),'errors':errors}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--scope',action='append')
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args()
    result=run_lint(args.root,args.scope)
    print(json.dumps(result,ensure_ascii=False,indent=2) if args.json else f"문서 {result['files']}개 · 오류 {len(result['errors'])}건")
    if not args.json:
        for e in result['errors']: print(f"{e['file']} · {e['item']} · {e['detail']}")
    return 1 if result['errors'] else 0
if __name__=='__main__': sys.exit(main())
