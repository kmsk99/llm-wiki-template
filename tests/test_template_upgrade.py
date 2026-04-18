import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


upgrader = load_module('template_upgrade', 'scripts/template_upgrade.py')


class TemplateUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.source = self.root / 'source'
        self.target = self.root / 'target'
        self.source.mkdir()
        self.target.mkdir()

        (self.source / '.agents/skills/catalog').mkdir(parents=True)
        (self.source / '.agents/skills/catalog/SKILL.md').write_text('catalog skill\n', encoding='utf-8')
        (self.source / '.claude/commands').mkdir(parents=True)
        (self.source / '.claude/commands/catalog.md').write_text('catalog command\n', encoding='utf-8')
        (self.source / 'SCHEMA.md').write_text('schema v2\n', encoding='utf-8')
        (self.source / '.claude').mkdir(exist_ok=True)
        (self.source / '.claude/settings.json').write_text(
            json.dumps(
                {
                    'hooks': {
                        'PreToolUse': [
                            {
                                'matcher': 'Glob|Grep',
                                'hooks': [
                                    {
                                        'type': 'command',
                                        'command': 'graphify-hook',
                                    }
                                ],
                            }
                        ]
                    }
                },
                ensure_ascii=False,
                indent=2,
            ) + '\n',
            encoding='utf-8',
        )
        (self.source / '.gitignore').write_text(
            '\n'.join(
                [
                    '# base',
                    '# >>> llm-wiki-template graphify >>>',
                    'graphify-out/cache/',
                    'graphify-out/.graphify_python',
                    '# <<< llm-wiki-template graphify <<<',
                    '',
                ]
            ),
            encoding='utf-8',
        )

        self.manifest = {
            'manifest_version': 1,
            'replace_paths': ['.agents/skills', '.claude/commands', 'SCHEMA.md'],
            'json_merges': [{'path': '.claude/settings.json', 'strategy': 'deep_merge_unique'}],
            'block_merges': [
                {
                    'path': '.gitignore',
                    'source_path': '.gitignore',
                    'start_marker': '# >>> llm-wiki-template graphify >>>',
                    'end_marker': '# <<< llm-wiki-template graphify <<<',
                }
            ],
            'exclude_paths': ['graphify-out'],
        }

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_dry_run_does_not_modify_target(self):
        operations = upgrader.upgrade_target(self.source, self.target, self.manifest, apply=False)

        self.assertFalse((self.target / 'SCHEMA.md').exists())
        self.assertFalse((self.target / upgrader.LOCK_FILENAME).exists())
        self.assertTrue(any(op.status == 'planned' for op in operations))

    def test_apply_replaces_managed_paths_and_merges_settings(self):
        (self.target / '.agents/skills/old').mkdir(parents=True)
        (self.target / '.agents/skills/old/SKILL.md').write_text('old skill\n', encoding='utf-8')
        (self.target / '.claude/commands').mkdir(parents=True)
        (self.target / '.claude/commands/old.md').write_text('old command\n', encoding='utf-8')
        (self.target / 'SCHEMA.md').write_text('custom schema\n', encoding='utf-8')
        (self.target / '.claude').mkdir(exist_ok=True)
        (self.target / '.claude/settings.json').write_text(
            json.dumps(
                {
                    'customSetting': True,
                    'hooks': {
                        'PreToolUse': [
                            {
                                'matcher': 'Read',
                                'hooks': [{'type': 'command', 'command': 'custom-hook'}],
                            }
                        ]
                    },
                },
                ensure_ascii=False,
                indent=2,
            ) + '\n',
            encoding='utf-8',
        )
        (self.target / '.gitignore').write_text('# custom\n', encoding='utf-8')

        operations = upgrader.upgrade_target(self.source, self.target, self.manifest, apply=True, force=True)

        self.assertFalse((self.target / '.agents/skills/old').exists())
        self.assertEqual((self.target / '.agents/skills/catalog/SKILL.md').read_text(encoding='utf-8'), 'catalog skill\n')
        self.assertFalse((self.target / '.claude/commands/old.md').exists())
        self.assertEqual((self.target / 'SCHEMA.md').read_text(encoding='utf-8'), 'schema v2\n')

        settings = json.loads((self.target / '.claude/settings.json').read_text(encoding='utf-8'))
        self.assertTrue(settings['customSetting'])
        pre_tool_use = settings['hooks']['PreToolUse']
        self.assertEqual(len(pre_tool_use), 2)
        self.assertIn({'type': 'command', 'command': 'custom-hook'}, pre_tool_use[0]['hooks'])
        self.assertIn({'type': 'command', 'command': 'graphify-hook'}, pre_tool_use[1]['hooks'])

        gitignore = (self.target / '.gitignore').read_text(encoding='utf-8')
        self.assertIn('# custom', gitignore)
        self.assertEqual(gitignore.count('# >>> llm-wiki-template graphify >>>'), 1)
        self.assertIn('graphify-out/cache/', gitignore)

        lock = json.loads((self.target / upgrader.LOCK_FILENAME).read_text(encoding='utf-8'))
        self.assertEqual(lock['schema_version'], upgrader.LOCK_SCHEMA_VERSION)
        self.assertEqual(lock['manifest_version'], 1)
        self.assertIn('.agents/skills', lock['managed_targets']['replace_paths'])
        self.assertTrue(any(op.status == 'updated' for op in operations))

    def test_apply_merges_same_matcher_hooks_into_one_entry(self):
        (self.target / '.claude').mkdir(exist_ok=True)
        (self.target / '.claude/settings.json').write_text(
            json.dumps(
                {
                    'hooks': {
                        'PreToolUse': [
                            {
                                'matcher': 'Glob|Grep',
                                'hooks': [{'type': 'command', 'command': 'custom-hook'}],
                            }
                        ]
                    }
                },
                ensure_ascii=False,
                indent=2,
            ) + '\n',
            encoding='utf-8',
        )

        upgrader.upgrade_target(self.source, self.target, self.manifest, apply=True)

        settings = json.loads((self.target / '.claude/settings.json').read_text(encoding='utf-8'))
        entries = settings['hooks']['PreToolUse']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['matcher'], 'Glob|Grep')
        self.assertIn({'type': 'command', 'command': 'custom-hook'}, entries[0]['hooks'])
        self.assertIn({'type': 'command', 'command': 'graphify-hook'}, entries[0]['hooks'])

    def test_second_apply_is_idempotent(self):
        upgrader.upgrade_target(self.source, self.target, self.manifest, apply=True)
        operations = upgrader.upgrade_target(self.source, self.target, self.manifest, apply=True)

        self.assertTrue(all(op.status == 'noop' for op in operations))
        gitignore = (self.target / '.gitignore').read_text(encoding='utf-8')
        self.assertEqual(gitignore.count('# >>> llm-wiki-template graphify >>>'), 1)

    def test_apply_refuses_to_overwrite_unmanaged_replace_path_without_force(self):
        (self.target / 'SCHEMA.md').write_text('local override\n', encoding='utf-8')

        with self.assertRaises(upgrader.UpgradeError):
            upgrader.upgrade_target(self.source, self.target, self.manifest, apply=True)

    def test_apply_refuses_to_overwrite_modified_managed_block_without_force(self):
        upgrader.upgrade_target(self.source, self.target, self.manifest, apply=True)
        (self.target / '.gitignore').write_text(
            '# >>> llm-wiki-template graphify >>>\nmodified\n# <<< llm-wiki-template graphify <<<\n',
            encoding='utf-8',
        )

        with self.assertRaises(upgrader.UpgradeError):
            upgrader.upgrade_target(self.source, self.target, self.manifest, apply=True)

    def test_apply_refuses_to_overwrite_unmanaged_existing_block_without_force(self):
        (self.target / '.gitignore').write_text(
            '# >>> llm-wiki-template graphify >>>\ncustom block\n# <<< llm-wiki-template graphify <<<\n',
            encoding='utf-8',
        )

        with self.assertRaises(upgrader.UpgradeError):
            upgrader.upgrade_target(self.source, self.target, self.manifest, apply=True)

    def test_invalid_target_json_raises_upgrade_error(self):
        (self.target / '.claude').mkdir(exist_ok=True)
        (self.target / '.claude/settings.json').write_text('{invalid json\n', encoding='utf-8')

        with self.assertRaises(upgrader.UpgradeError):
            upgrader.upgrade_target(self.source, self.target, self.manifest, apply=True)

    def test_invalid_lockfile_raises_upgrade_error(self):
        (self.target / upgrader.LOCK_FILENAME).write_text('{invalid json\n', encoding='utf-8')

        with self.assertRaises(upgrader.UpgradeError):
            upgrader.upgrade_target(self.source, self.target, self.manifest, apply=False)

    def test_manifest_path_traversal_is_rejected(self):
        bad_manifest = dict(self.manifest)
        bad_manifest['replace_paths'] = ['../../escape.txt']

        with self.assertRaises(upgrader.UpgradeError):
            upgrader.upgrade_target(self.source, self.target, bad_manifest, apply=False)


if __name__ == '__main__':
    unittest.main()
