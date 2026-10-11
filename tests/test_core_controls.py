import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import lint_wiki
import template_upgrade

META = '---\ntitle: Example\nowner: reader\nstatus: draft\nupdated: 2026-10-12\ntags: []\nsource: []\n'

class CoreControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(REPO / 'scripts', self.root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        (self.root / 'wiki').mkdir()
        (self.root / 'raw').mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'core.hooksPath', str(self.root / '.git/hooks'))
        (self.root / 'raw/source.md').write_text('original\n')
        (self.root / 'raw/.manifest.md').write_text('registered\n')
        self.git('add', 'raw', 'scripts')
        self.git('commit', '-qm', 'fixture')

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, text=True, capture_output=True, check=True)

    def script(self, name, *args):
        return subprocess.run([sys.executable, str(self.root/'scripts'/name), *map(str,args)], cwd=self.root, text=True, capture_output=True)

    def page(self, extra='', body=''):
        p=self.root/'wiki/example.md'
        p.write_text(META+extra+'---\n'+body)
        return p

    def test_new_raw_and_manifest_edit_allowed(self):
        (self.root/'raw/new.md').write_text('new\n')
        (self.root/'raw/.manifest.md').write_text('new registration\n')
        self.git('add','raw')
        self.assertEqual(self.script('check_raw_immutable.py').returncode,0)

    def test_raw_mutation_delete_move_and_type_are_blocked(self):
        for change in ['modify','delete','move','type']:
            with self.subTest(change=change):
                self.git('reset','--hard','HEAD')
                p=self.root/'raw/source.md'
                if change=='modify': p.write_text('changed')
                elif change=='delete': p.unlink()
                elif change=='move': p.rename(self.root/'moved.md')
                else:
                    p.unlink(); p.symlink_to('.manifest.md')
                self.git('add','-A')
                self.assertEqual(self.script('check_raw_immutable.py').returncode,1)

    def test_manifest_delete_blocked(self):
        (self.root/'raw/.manifest.md').unlink();self.git('add','raw')
        self.assertEqual(self.script('check_raw_immutable.py').returncode,1)

    def test_scanner_reads_index_and_redacts(self):
        token='ghp_'+'a'*36
        p=self.root/'example.txt';p.write_text(token);self.git('add','example.txt')
        p.write_text('worktree is clean')
        result=self.script('check_secrets.py')
        self.assertEqual(result.returncode,1)
        self.assertNotIn(token,result.stdout+result.stderr)

    def test_existing_hook_preserved(self):
        hook=self.root/'.git/hooks/pre-commit';hook.write_text('#!/bin/sh\necho custom\n')
        result=self.script('install_hooks.py')
        self.assertEqual(result.returncode,1)
        self.assertEqual(hook.read_text(),'#!/bin/sh\necho custom\n')

    def test_managed_hook_idempotent_and_blocks_commit(self):
        self.assertEqual(self.script('install_hooks.py').returncode,0)
        self.assertEqual(self.script('install_hooks.py').returncode,0)
        (self.root/'raw/source.md').write_text('changed')
        self.git('add','raw')
        result=subprocess.run(['git','commit','-qm','should fail'],cwd=self.root,capture_output=True)
        self.assertNotEqual(result.returncode,0)

    def test_lint_metadata_links_and_sources(self):
        p=self.page('verified: true\n', '[broken](missing.md)\n[[Missing Wiki]]\n')
        p.write_text(p.read_text().replace('source: []','source: [raw/not-found.md]'))
        kinds={e['item'] for e in lint_wiki.run_lint(self.root)['errors']}
        self.assertTrue({'verified','link','wikilink','source'} <= kinds)

    def test_valid_source_and_verified_metadata(self):
        p=self.page('verified: true\nverified_by: Reader\nverified_at: 2026-10-12\n', '[source](../raw/source.md)')
        p.write_text(p.read_text().replace('source: []','source:\n  - raw/source.md'))
        self.assertEqual(lint_wiki.run_lint(self.root)['errors'],[])

    def test_duplicate_yaml_and_string_boolean_fail(self):
        self.page('verified: "true"\n')
        self.assertTrue(lint_wiki.run_lint(self.root)['errors'])
        self.page('title: Duplicate\n')
        self.assertEqual(lint_wiki.run_lint(self.root)['errors'][0]['item'],'frontmatter')

    def test_examples_comments_anchors_and_urls_ignored(self):
        self.page(body='<!-- [example](absent.md) -->\n```md\n[example](absent.md)\n```\n[x](#heading)\n[x](https://example.invalid)')
        self.assertEqual(lint_wiki.run_lint(self.root)['errors'],[])

    def test_gate_preserves_old_debt_but_fails_new_error(self):
        p=self.page(body='[old](old.md)')
        baseline=self.root/'before.json'
        self.assertEqual(self.script('lint_gate.py','save',baseline).returncode,0)
        self.assertEqual(self.script('lint_gate.py','check',baseline).returncode,0)
        p.write_text(p.read_text()+'\n[new](new.md)')
        self.assertEqual(self.script('lint_gate.py','check',baseline).returncode,1)
        data=json.loads(baseline.read_text());data['root']='/different';baseline.write_text(json.dumps(data))
        self.assertEqual(self.script('lint_gate.py','check',baseline).returncode,2)

    def test_sync_detects_drift_and_keeps_unmanaged_files(self):
        source=self.root/'.claude/commands/demo.md';source.parent.mkdir(parents=True)
        source.write_text('---\nname: demo\ndescription: Demo\n---\n# Demo\n')
        extra=self.root/'.agents/skills/custom/SKILL.md';extra.parent.mkdir(parents=True);extra.write_text('user')
        self.assertEqual(self.script('sync_codex_skills.py').returncode,0)
        self.assertEqual(extra.read_text(),'user')
        source.write_text(source.read_text()+'changed\n')
        self.assertEqual(self.script('sync_codex_skills.py','--check').returncode,1)
        self.assertEqual(self.script('sync_codex_skills.py').returncode,0)

    def test_sync_refuses_unmanaged_collision(self):
        source=self.root/'.claude/commands/demo.md';source.parent.mkdir(parents=True)
        source.write_text('---\nname: demo\ndescription: Demo\n---\n# Demo\n')
        target=self.root/'.agents/skills/demo/SKILL.md';target.parent.mkdir(parents=True);target.write_text('custom')
        self.assertEqual(self.script('sync_codex_skills.py').returncode,1)
        self.assertEqual(target.read_text(),'custom')

class RealUpgrade(unittest.TestCase):
    def test_actual_manifest_preserves_user_data_and_idempotence(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)
            manifest=template_upgrade.load_manifest(REPO/'scripts/template_upgrade_manifest.json')
            for name in ['PROJECT.md','.agents/skills/user/SKILL.md','templates/user.md','wiki/user.md','raw/user.md','output/user.md','AGENTS.md']:
                p=target/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('user-owned\n')
            before={str(p.relative_to(target)):p.read_bytes() for p in target.rglob('*') if p.is_file()}
            template_upgrade.upgrade_target(REPO,target,manifest,apply=False)
            self.assertEqual(before,{str(p.relative_to(target)):p.read_bytes() for p in target.rglob('*') if p.is_file()})
            template_upgrade.upgrade_target(REPO,target,manifest,apply=True)
            for name,data in before.items():
                if name=='AGENTS.md': self.assertIn(data.decode(),(target/name).read_text())
                else: self.assertEqual((target/name).read_bytes(),data)
            template_upgrade.upgrade_target(REPO,target,manifest,apply=True)
            (target/'SCHEMA.md').write_text('user edit')
            with self.assertRaises(template_upgrade.UpgradeError): template_upgrade.upgrade_target(REPO,target,manifest,apply=True)

    def test_legacy_directory_lock_migrates_only_if_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';target=root/'target'
            (source/'skills').mkdir(parents=True);(target/'skills').mkdir(parents=True)
            (source/'skills/a.md').write_text('new');(target/'skills/a.md').write_text('old')
            lock={'files':{'skills':{'applied_hash':template_upgrade.path_digest(target/'skills')}}}
            self.assertIsNone(template_upgrade.replace_conflict_message('skills/a.md',source/'skills/a.md',target/'skills/a.md',lock))
            (target/'skills/a.md').write_text('local edit')
            self.assertIsNotNone(template_upgrade.replace_conflict_message('skills/a.md',source/'skills/a.md',target/'skills/a.md',lock))

if __name__=='__main__':unittest.main()
