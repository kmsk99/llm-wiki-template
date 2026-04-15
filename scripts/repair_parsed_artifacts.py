#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / 'raw'
PARSE_SCRIPT = ROOT / 'scripts' / 'parse-raw.sh'
SIZE_SUFFIX_RE = re.compile(r'(?:-\(|\()(?:(?:\d+(?:\.\d+)?)-?(?:KB|MB|K))\)$', re.I)
MOJIBAKE_CHARS = ('ì', 'ë', 'ê', 'ã', '\x84', '\x87', '\x90')
PARSEABLE_EXTS = {
    '.pdf', '.doc', '.docx', '.pptx', '.xlsx', '.xls', '.hwp', '.hwpx',
    '.png', '.jpg', '.jpeg', '.gif', '.tiff', '.bmp', '.epub', '.html', '.htm',
    '.csv', '.txt', '.json', '.xml', '.wav', '.mp3',
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Repair stale parsed artifacts and suspicious duplicate raw filenames.')
    parser.add_argument('--raw-dir', type=Path, default=RAW_ROOT)
    parser.add_argument('--min-bytes', type=int, default=2)
    parser.add_argument('--dry-run', action='store_true')
    return parser.parse_args()


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_output_path(path: Path) -> Path:
    parsed = path.with_suffix(path.suffix + '.parsed.md') if path.suffix else path.with_name(path.name + '.parsed.md')
    if not parsed.exists() and path.suffix:
        alt = path.with_name(path.stem + '.parsed.md')
        return alt
    return parsed


def looks_mojibake(text: str) -> bool:
    return any(ch in text for ch in MOJIBAKE_CHARS)


def cleaned_filename_hint(text: str) -> str:
    return SIZE_SUFFIX_RE.sub('', text).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def needs_parse_refresh(path: Path, min_bytes: int) -> bool:
    if path.suffix.lower() not in PARSEABLE_EXTS:
        return False
    parsed = parse_output_path(path)
    return (not parsed.exists()) or parsed.stat().st_size < min_bytes or path.stat().st_mtime > parsed.stat().st_mtime


def run_parse(path: Path, dry_run: bool) -> dict[str, object]:
    if dry_run:
        return {'action': 'reparse', 'path': display_path(path), 'dry_run': True}
    result = subprocess.run([str(PARSE_SCRIPT), str(path)], cwd=str(ROOT), capture_output=True, text=True)
    return {
        'action': 'reparse',
        'path': display_path(path),
        'ok': result.returncode == 0,
        'stdout': result.stdout[-1000:],
        'stderr': result.stderr[-1000:],
    }


def remove_with_parsed(path: Path, dry_run: bool) -> list[str]:
    removed = [display_path(path)]
    parsed = parse_output_path(path)
    if parsed.exists():
        removed.append(display_path(parsed))
    if dry_run:
        return removed
    if path.exists():
        path.unlink()
    if parsed.exists():
        parsed.unlink()
    return removed


def rename_with_parsed(path: Path, new_path: Path, dry_run: bool) -> list[str]:
    actions = [f'{display_path(path)} -> {display_path(new_path)}']
    old_parsed = parse_output_path(path)
    new_parsed = parse_output_path(new_path)
    if old_parsed.exists() and old_parsed != new_parsed:
        actions.append(f'{display_path(old_parsed)} -> {display_path(new_parsed)}')
    if dry_run:
        return actions
    path.rename(new_path)
    if old_parsed.exists() and old_parsed != new_parsed:
        if new_parsed.exists():
            old_parsed.unlink()
        else:
            old_parsed.rename(new_parsed)
    return actions


def canonical_duplicate(path: Path) -> Optional[Path]:
    for sibling in sorted(path.parent.iterdir()):
        if sibling == path or not sibling.is_file() or sibling.name.endswith('.parsed.md'):
            continue
        if looks_mojibake(sibling.name) or SIZE_SUFFIX_RE.search(sibling.name):
            continue
        try:
            if sibling.stat().st_size == path.stat().st_size and sha256(sibling) == sha256(path):
                return sibling
        except OSError:
            continue
    return None


def repair_filename(path: Path, dry_run: bool) -> Optional[dict[str, object]]:
    if not path.exists() or path.name.endswith('.parsed.md'):
        return None
    if not looks_mojibake(path.name) and not SIZE_SUFFIX_RE.search(path.name):
        return None
    duplicate = canonical_duplicate(path)
    if duplicate is not None:
        removed = remove_with_parsed(path, dry_run)
        return {'action': 'dedupe', 'target': display_path(path), 'canonical': display_path(duplicate), 'removed': removed}
    stripped_name = cleaned_filename_hint(path.name)
    new_path = path.with_name(stripped_name)
    if stripped_name != path.name and not new_path.exists():
        actions = rename_with_parsed(path, new_path, dry_run)
        return {'action': 'rename', 'target': display_path(path), 'renamed': actions}
    return None


def iter_raw_files(raw_dir: Path) -> Iterable[Path]:
    for path in sorted(raw_dir.rglob('*')):
        if path.is_file() and path.name != '.manifest.md' and not path.name.endswith('.parsed.md'):
            yield path


def main() -> int:
    args = parse_args()
    summary = {'reparsed': [], 'filename_repairs': []}
    for path in iter_raw_files(args.raw_dir):
        repair = repair_filename(path, args.dry_run)
        if repair:
            summary['filename_repairs'].append(repair)
            continue
        if needs_parse_refresh(path, args.min_bytes):
            summary['reparsed'].append(run_parse(path, args.dry_run))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
