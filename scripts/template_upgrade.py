#!/usr/bin/env python3
"""Upgrade one or more llm-wiki-template-based projects from this template repo."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOCK_FILENAME = '.llmwiki-template-lock.json'
LOCK_SCHEMA_VERSION = 1
DEFAULT_MANIFEST = Path(__file__).with_name('template_upgrade_manifest.json')


@dataclass
class Operation:
    kind: str
    path: str
    status: str
    detail: str = ''


class UpgradeError(RuntimeError):
    """Raised when a target cannot be upgraded safely."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise UpgradeError(f'Invalid JSON in manifest: {path}') from exc


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def deep_merge_preserve_existing(existing: Any, required: Any) -> Any:
    if isinstance(required, dict):
        base = existing if isinstance(existing, dict) else {}
        merged: dict[str, Any] = copy.deepcopy(base)
        for key, value in required.items():
            merged[key] = deep_merge_preserve_existing(base.get(key), value)
        return merged

    if isinstance(required, list):
        base_list = copy.deepcopy(existing if isinstance(existing, list) else [])
        seen = {canonical_json(item) for item in base_list}
        for item in required:
            fingerprint = canonical_json(item)
            if fingerprint not in seen:
                base_list.append(copy.deepcopy(item))
                seen.add(fingerprint)
        return base_list

    if existing is None:
        return copy.deepcopy(required)
    return copy.deepcopy(existing)


def merge_named_hook_lists(existing_items: list[Any], required_items: list[Any]) -> list[Any]:
    merged = copy.deepcopy(existing_items)
    matcher_index = {
        item.get('matcher'): index
        for index, item in enumerate(merged)
        if isinstance(item, dict) and item.get('matcher') is not None
    }
    seen = {canonical_json(item) for item in merged}

    for required in required_items:
        if not isinstance(required, dict) or required.get('matcher') is None:
            fingerprint = canonical_json(required)
            if fingerprint not in seen:
                merged.append(copy.deepcopy(required))
                seen.add(fingerprint)
            continue

        matcher = required['matcher']
        if matcher not in matcher_index:
            merged.append(copy.deepcopy(required))
            matcher_index[matcher] = len(merged) - 1
            seen.add(canonical_json(required))
            continue

        existing_item = merged[matcher_index[matcher]]
        combined = deep_merge_preserve_existing(existing_item, required)
        existing_hooks = existing_item.get('hooks', []) if isinstance(existing_item, dict) else []
        required_hooks = required.get('hooks', []) if isinstance(required, dict) else []
        combined['hooks'] = deep_merge_preserve_existing(existing_hooks, required_hooks)
        merged[matcher_index[matcher]] = combined

    return merged


def merge_claude_settings(existing_payload: Any, required_payload: Any) -> Any:
    existing = existing_payload if isinstance(existing_payload, dict) else {}
    required = required_payload if isinstance(required_payload, dict) else {}
    merged = copy.deepcopy(existing)

    for key, value in required.items():
        if key != 'hooks':
            merged[key] = deep_merge_preserve_existing(existing.get(key), value)

    existing_hooks = existing.get('hooks', {}) if isinstance(existing.get('hooks'), dict) else {}
    required_hooks = required.get('hooks', {}) if isinstance(required.get('hooks'), dict) else {}
    hooks_result = copy.deepcopy(existing_hooks)
    for event_name, required_items in required_hooks.items():
        existing_items = hooks_result.get(event_name, []) if isinstance(hooks_result.get(event_name), list) else []
        hooks_result[event_name] = merge_named_hook_lists(existing_items, required_items if isinstance(required_items, list) else [])
    if hooks_result:
        merged['hooks'] = hooks_result
    return merged


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def hash_tree(path: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(p for p in path.rglob('*') if p.is_file()):
        digest.update(str(child.relative_to(path)).encode('utf-8'))
        digest.update(b'\0')
        digest.update(hash_file(child).encode('ascii'))
        digest.update(b'\0')
    return digest.hexdigest()


def text_digest(text: str) -> str:
    return 'sha256:' + hashlib.sha256(text.encode('utf-8')).hexdigest()


def path_digest(path: Path) -> str | None:
    if not path.exists():
        return None
    if path.is_file():
        return f'sha256:{hash_file(path)}'
    return f'sha256:{hash_tree(path)}'


def paths_equal(source: Path, target: Path) -> bool:
    if not target.exists() or source.is_dir() != target.is_dir():
        return False
    return path_digest(source) == path_digest(target)


def resolve_under(root: Path, relative_path: str) -> Path:
    root_resolved = root.resolve()
    candidate = (root / relative_path).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise UpgradeError(f'Path escapes managed root: {relative_path}')
    return candidate


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def copy_path(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        if target.exists():
            remove_path(target)
        shutil.copytree(source, target)
    else:
        if target.exists() or target.is_symlink():
            remove_path(target)
        shutil.copy2(source, target)


def extract_block(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1 or end < start:
        raise UpgradeError(f'Markers not found: {start_marker} / {end_marker}')
    end += len(end_marker)
    block = text[start:end]
    return block if block.endswith('\n') else block + '\n'


def extract_block_from_file(path: Path, start_marker: str, end_marker: str) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding='utf-8')
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1 or end < start:
        return None
    end += len(end_marker)
    block = text[start:end]
    return block if block.endswith('\n') else block + '\n'


def merge_block(target_text: str, block: str, start_marker: str, end_marker: str) -> str:
    start = target_text.find(start_marker)
    end = target_text.find(end_marker)
    if start != -1 and end != -1 and end > start:
        end += len(end_marker)
        if end < len(target_text) and target_text[end:end + 1] == '\n':
            end += 1
        merged = target_text[:start] + block + target_text[end:]
    else:
        stripped = target_text.rstrip('\n')
        merged = block if not stripped else stripped + '\n\n' + block
    return merged if merged.endswith('\n') else merged + '\n'


def load_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise UpgradeError(f'Invalid JSON file: {path}') from exc


def dump_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def git_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ['git', '-C', str(root), 'rev-parse', 'HEAD'],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None


def ensure_target_dir(target_root: Path, template_root: Path) -> None:
    if not target_root.exists() or not target_root.is_dir():
        raise UpgradeError(f'Target directory not found: {target_root}')
    if target_root.resolve() == template_root.resolve():
        raise UpgradeError('Target directory must not be the template repository itself')


def validate_manifest_paths(template_root: Path, manifest: dict[str, Any]) -> None:
    excluded = [Path(path).parts for path in manifest.get('exclude_paths', [])]

    def assert_not_excluded(relative_path: str) -> None:
        parts = Path(relative_path).parts
        for excluded_parts in excluded:
            if parts[: len(excluded_parts)] == excluded_parts:
                raise UpgradeError(f'Managed path overlaps excluded path: {relative_path}')

    for relative_path in manifest.get('replace_paths', []):
        resolve_under(template_root, relative_path)
        assert_not_excluded(relative_path)
    for item in manifest.get('json_merges', []):
        resolve_under(template_root, item['path'])
        assert_not_excluded(item['path'])
    for item in manifest.get('block_merges', []):
        resolve_under(template_root, item['path'])
        resolve_under(template_root, item['source_path'])
        assert_not_excluded(item['path'])


def load_lockfile(target_root: Path) -> dict[str, Any] | None:
    lock_path = target_root / LOCK_FILENAME
    if not lock_path.exists():
        return None
    return load_json_file(lock_path)


def replace_conflict_message(relative_path: str, source: Path, target: Path, lock_payload: dict[str, Any] | None) -> str | None:
    if not target.exists() or paths_equal(source, target):
        return None
    if not lock_payload:
        return f'{relative_path}: existing unmanaged content differs from template'
    entry = lock_payload.get('files', {}).get(relative_path)
    if not entry:
        return f'{relative_path}: existing content differs and has no lock entry'
    current_hash = path_digest(target)
    if current_hash != entry.get('applied_hash'):
        return f'{relative_path}: local modifications detected since last template apply'
    return None


def merge_conflict_message(relative_path: str, current_hash: str | None, lock_payload: dict[str, Any] | None) -> str | None:
    if not lock_payload:
        return None
    entry = lock_payload.get('files', {}).get(relative_path)
    if not entry:
        return None
    if current_hash != entry.get('applied_hash'):
        return f'{relative_path}: local modifications detected since last template apply'
    return None


def block_conflict_message(
    relative_path: str,
    source_block_hash: str,
    target_block_hash: str | None,
    lock_payload: dict[str, Any] | None,
) -> str | None:
    if target_block_hash is None:
        return None
    if not lock_payload:
        if target_block_hash != source_block_hash:
            return f'{relative_path}: existing unmanaged block differs from template'
        return None
    entry = lock_payload.get('files', {}).get(relative_path)
    if not entry:
        if target_block_hash != source_block_hash:
            return f'{relative_path}: existing managed block differs and has no lock entry'
        return None
    if target_block_hash != entry.get('applied_hash'):
        return f'{relative_path}: local modifications detected since last template apply'
    return None


def current_block_hash(target: Path, start_marker: str, end_marker: str) -> str | None:
    block = extract_block_from_file(target, start_marker, end_marker)
    return text_digest(block) if block is not None else None


def preflight_writes(
    template_root: Path,
    target_root: Path,
    manifest: dict[str, Any],
    lock_payload: dict[str, Any] | None,
    force: bool,
) -> None:
    if force:
        return

    conflicts: list[str] = []

    for relative_path in manifest.get('replace_paths', []):
        source = resolve_under(template_root, relative_path)
        target = resolve_under(target_root, relative_path)
        if not source.exists():
            raise UpgradeError(f'Managed source path missing: {relative_path}')
        message = replace_conflict_message(relative_path, source, target, lock_payload)
        if message:
            conflicts.append(message)

    for item in manifest.get('json_merges', []):
        target = resolve_under(target_root, item['path'])
        message = merge_conflict_message(item['path'], path_digest(target), lock_payload)
        if message:
            conflicts.append(message)

    for item in manifest.get('block_merges', []):
        target = resolve_under(target_root, item['path'])
        source_block = extract_block(
            resolve_under(template_root, item['source_path']).read_text(encoding='utf-8'),
            item['start_marker'],
            item['end_marker'],
        )
        message = block_conflict_message(
            item['path'],
            text_digest(source_block),
            current_block_hash(target, item['start_marker'], item['end_marker']),
            lock_payload,
        )
        if message:
            conflicts.append(message)

    if conflicts:
        raise UpgradeError('Refusing to overwrite managed paths:\n- ' + '\n- '.join(conflicts) + '\nUse --force to override.')


def sync_replace_path(template_root: Path, target_root: Path, relative_path: str, apply: bool) -> Operation:
    source = resolve_under(template_root, relative_path)
    target = resolve_under(target_root, relative_path)
    if not source.exists():
        raise UpgradeError(f'Managed source path missing: {relative_path}')
    if paths_equal(source, target):
        return Operation('replace', relative_path, 'noop')
    if apply:
        copy_path(source, target)
        return Operation('replace', relative_path, 'updated')
    return Operation('replace', relative_path, 'planned')


def sync_json_merge(template_root: Path, target_root: Path, relative_path: str, apply: bool) -> tuple[Operation, Any]:
    source = resolve_under(template_root, relative_path)
    target = resolve_under(target_root, relative_path)
    if not source.exists():
        raise UpgradeError(f'JSON merge source missing: {relative_path}')
    source_payload = load_json_file(source)
    existing_payload = load_json_file(target) if target.exists() else {}
    merged_payload = merge_claude_settings(existing_payload, source_payload)
    if canonical_json(existing_payload) == canonical_json(merged_payload):
        return Operation('json-merge', relative_path, 'noop'), existing_payload
    if apply:
        dump_json_file(target, merged_payload)
        return Operation('json-merge', relative_path, 'updated'), merged_payload
    return Operation('json-merge', relative_path, 'planned'), merged_payload


def sync_block_merge(
    template_root: Path,
    target_root: Path,
    relative_path: str,
    source_path: str,
    start_marker: str,
    end_marker: str,
    apply: bool,
) -> tuple[Operation, str]:
    source_text = resolve_under(template_root, source_path).read_text(encoding='utf-8')
    block = extract_block(source_text, start_marker, end_marker)
    target = resolve_under(target_root, relative_path)
    target_text = target.read_text(encoding='utf-8') if target.exists() else ''
    merged_text = merge_block(target_text, block, start_marker, end_marker)
    detail = f'{start_marker}..{end_marker}'
    if target_text == merged_text:
        return Operation('block-merge', relative_path, 'noop', detail), block
    if apply:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(merged_text, encoding='utf-8')
        return Operation('block-merge', relative_path, 'updated', detail), block
    return Operation('block-merge', relative_path, 'planned', detail), block


def build_lock_payload(
    template_root: Path,
    manifest: dict[str, Any],
    file_entries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        'schema_version': LOCK_SCHEMA_VERSION,
        'template_root': str(template_root.resolve()),
        'template_commit': git_commit(template_root),
        'manifest_version': manifest.get('manifest_version'),
        'applied_at': utc_now_iso(),
        'managed_targets': {
            'replace_paths': manifest.get('replace_paths', []),
            'json_merges': [item['path'] for item in manifest.get('json_merges', [])],
            'block_merges': [item['path'] for item in manifest.get('block_merges', [])],
            'exclude_paths': manifest.get('exclude_paths', []),
        },
        'files': file_entries,
    }


def write_lockfile(
    template_root: Path,
    target_root: Path,
    manifest: dict[str, Any],
    file_entries: dict[str, dict[str, Any]],
    apply: bool,
) -> Operation:
    payload = build_lock_payload(template_root, manifest, file_entries)
    lock_path = target_root / LOCK_FILENAME
    current = load_json_file(lock_path) if lock_path.exists() else None
    if current is not None:
        comparable_new = copy.deepcopy(payload)
        comparable_new['applied_at'] = current.get('applied_at')
        if canonical_json(current) == canonical_json(comparable_new):
            return Operation('lockfile', LOCK_FILENAME, 'noop')
    if apply:
        dump_json_file(lock_path, payload)
        return Operation('lockfile', LOCK_FILENAME, 'updated')
    return Operation('lockfile', LOCK_FILENAME, 'planned')


def upgrade_target(
    template_root: Path,
    target_root: Path,
    manifest: dict[str, Any],
    apply: bool,
    force: bool = False,
) -> list[Operation]:
    ensure_target_dir(target_root, template_root)
    validate_manifest_paths(template_root, manifest)
    lock_payload = load_lockfile(target_root)
    preflight_writes(template_root, target_root, manifest, lock_payload, force=force)

    operations: list[Operation] = []
    file_entries: dict[str, dict[str, Any]] = {}

    for relative_path in manifest.get('replace_paths', []):
        source = resolve_under(template_root, relative_path)
        target = resolve_under(target_root, relative_path)
        operation = sync_replace_path(template_root, target_root, relative_path, apply=apply)
        operations.append(operation)
        file_entries[relative_path] = {
            'mode': 'replace',
            'upstream_hash': path_digest(source),
            'applied_hash': path_digest(target) if apply or operation.status == 'noop' else path_digest(source),
        }

    for item in manifest.get('json_merges', []):
        target = resolve_under(target_root, item['path'])
        operation, merged_payload = sync_json_merge(template_root, target_root, item['path'], apply=apply)
        operations.append(operation)
        planned_hash = text_digest(json.dumps(merged_payload, ensure_ascii=False, indent=2) + '\n')
        file_entries[item['path']] = {
            'mode': 'json-merge',
            'upstream_hash': path_digest(resolve_under(template_root, item['path'])),
            'applied_hash': path_digest(target) if apply or operation.status == 'noop' else planned_hash,
        }

    for item in manifest.get('block_merges', []):
        target = resolve_under(target_root, item['path'])
        operation, source_block = sync_block_merge(
            template_root,
            target_root,
            item['path'],
            item['source_path'],
            item['start_marker'],
            item['end_marker'],
            apply=apply,
        )
        operations.append(operation)
        file_entries[item['path']] = {
            'mode': 'block-merge',
            'upstream_hash': text_digest(source_block),
            'applied_hash': current_block_hash(target, item['start_marker'], item['end_marker']) if apply or operation.status == 'noop' else text_digest(source_block),
            'start_marker': item['start_marker'],
            'end_marker': item['end_marker'],
        }

    operations.append(write_lockfile(template_root, target_root, manifest, file_entries, apply=apply))
    return operations


def summarize_status(operations: list[Operation]) -> tuple[int, int]:
    changed = sum(1 for op in operations if op.status in {'updated', 'planned'})
    noop = sum(1 for op in operations if op.status == 'noop')
    return changed, noop


def print_report(target_root: Path, operations: list[Operation], apply: bool) -> None:
    mode = 'APPLY' if apply else 'DRY-RUN'
    changed, noop = summarize_status(operations)
    print(f'[{mode}] {target_root}')
    for op in operations:
        suffix = f' ({op.detail})' if op.detail else ''
        print(f'  - {op.kind:<11} {op.status:<7} {op.path}{suffix}')
    print(f'  Summary: {changed} change(s), {noop} unchanged\n')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('targets', nargs='+', help='Target project paths to upgrade')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry-run)')
    parser.add_argument('--force', action='store_true', help='Override managed-path conflict protection')
    parser.add_argument('--template-root', default=str(Path(__file__).resolve().parents[1]), help='Source template root')
    parser.add_argument('--manifest', default=str(DEFAULT_MANIFEST), help='Manifest JSON path')
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    template_root = Path(args.template_root).resolve()
    manifest = load_manifest(Path(args.manifest).resolve())

    failures = 0
    for raw_target in args.targets:
        target_root = Path(raw_target).expanduser().resolve()
        try:
            operations = upgrade_target(template_root, target_root, manifest, apply=args.apply, force=args.force)
        except UpgradeError as exc:
            failures += 1
            print(f'[ERROR] {target_root}: {exc}', file=sys.stderr)
            continue
        print_report(target_root, operations, apply=args.apply)

    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
