import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


env_defaults = load_module('env_defaults', 'scripts/env_defaults.py')
parse_image = load_module('parse_image', 'scripts/parse-image.py')
parse_hwp = load_module('parse_hwp', 'scripts/parse-hwp.py')
repair = load_module('repair_parsed_artifacts', 'scripts/repair_parsed_artifacts.py')


class EnvDefaultsTests(unittest.TestCase):
    def test_env_or_dotenv_reads_dotenv_when_env_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / '.env'
            env_file.write_text('CLIPROXY_API_KEY=test-key\n', encoding='utf-8')
            self.assertEqual(env_defaults.env_or_dotenv('CLIPROXY_API_KEY', env_file=env_file), 'test-key')


class ImageParserTests(unittest.TestCase):
    def test_build_markdown_uses_ocr_fallback_when_llm_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'sample.jpg'
            src.write_bytes(b'fakejpg')
            with mock.patch.object(parse_image, 'load_image_metadata', return_value=[]), \
                 mock.patch.object(parse_image, 'call_gpt_vision', return_value=(None, 'llm down')), \
                 mock.patch.object(parse_image, 'run_tesseract', return_value=('ocr text', None)):
                markdown = parse_image.build_markdown(src, use_llm=True, base_url='http://127.0.0.1:8317/v1', api_key='token', model='gpt-5.4-mini', timeout=30)
            self.assertIn('TODO: GPT vision unavailable or empty (llm down)', markdown)
            self.assertIn('## OCR Fallback', markdown)
            self.assertIn('ocr text', markdown)

    def test_build_markdown_skips_ocr_fallback_on_gpt_auth_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'sample.jpg'
            src.write_bytes(b'fakejpg')
            with mock.patch.object(parse_image, 'load_image_metadata', return_value=[]), \
                 mock.patch.object(parse_image, 'call_gpt_vision', return_value=(None, 'HTTP Error 401: Unauthorized')), \
                 mock.patch.object(parse_image, 'run_tesseract') as run_tesseract:
                markdown = parse_image.build_markdown(src, use_llm=True, base_url='http://127.0.0.1:8317/v1', api_key='token', model='gpt-5.4-mini', timeout=30)
            self.assertIn('GPT OAuth에 다시 로그인한 뒤 재시도하세요.', markdown)
            self.assertNotIn('## OCR Fallback', markdown)
            run_tesseract.assert_not_called()


class HwpParserTests(unittest.TestCase):
    def test_sniff_hwp_format_detects_hwpx_zip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'sample.hwpx'
            with zipfile.ZipFile(src, 'w') as zf:
                zf.writestr('Contents/section0.xml', '<root/>')
            self.assertEqual(parse_hwp.sniff_hwp_format(src), 'hwpx')


class RepairScriptTests(unittest.TestCase):
    def test_cleaned_filename_hint_strips_size_suffix(self):
        self.assertEqual(repair.cleaned_filename_hint('신청서.hwp(167.5-KB)'), '신청서.hwp')

    def test_repair_filename_removes_duplicate_mojibake_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bad = root / '[ë¶ì1]-ì°¸ê°ê¸°ì-ëª¨ì§-ê³µê³-ë¬¸.pdf'
            good = root / '[붙임1]-참가기업-모집-공고문.pdf'
            payload = b'%PDF-1.4 same'
            bad.write_bytes(payload)
            good.write_bytes(payload)
            bad_parsed = root / '[ë¶ì1]-ì°¸ê°ê¸°ì-ëª¨ì§-ê³µê³-ë¬¸.parsed.md'
            bad_parsed.write_text('parsed', encoding='utf-8')
            result = repair.repair_filename(bad, dry_run=False)
            self.assertEqual(result['action'], 'dedupe')
            self.assertFalse(bad.exists())
            self.assertFalse(bad_parsed.exists())


if __name__ == '__main__':
    unittest.main()
