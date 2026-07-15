import tempfile
import unittest
from pathlib import Path

from local_assistant import cache_key, estimate_tokens, is_text_file, load_config, query_terms, select_candidates


class LocalAssistantTests(unittest.TestCase):
    def test_query_terms_removes_common_korean_words(self):
        self.assertEqual(query_terms("로그인 관련 파일을 찾아 요약해줘"), ["로그인"])

    def test_selection_prioritizes_path_and_content_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "auth").mkdir()
            (root / "auth" / "LoginService.cs").write_text("class LoginService {}", encoding="utf-8")
            (root / "Unrelated.cs").write_text("class Unrelated {}", encoding="utf-8")
            selected, scanned_files, _ = select_candidates(root, "login service", 10, 10_000, 5_000, 10_000)
            self.assertEqual(scanned_files, 2)
            self.assertEqual(selected[0].relative, "auth/LoginService.cs")

    def test_large_file_does_not_consume_entire_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one.md").write_text("flow " * 10_000, encoding="utf-8")
            (root / "two.py").write_text("flow = True", encoding="utf-8")
            selected, _, _ = select_candidates(root, "flow", 10, 10_000, 5_000, 100_000)
            self.assertEqual(len(selected), 2)
            self.assertLessEqual(len(selected[0].text), 5_000)

    def test_selection_diversifies_code_tests_and_docs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "guide.md").write_text("wave " * 100, encoding="utf-8")
            (root / "Wave.cs").write_text("class Wave {}", encoding="utf-8")
            (root / "WaveTests.cs").write_text("class WaveTests {}", encoding="utf-8")
            selected, _, _ = select_candidates(root, "wave", 3, 10_000, 5_000, 100_000)
            self.assertEqual({item.relative for item in selected}, {"guide.md", "Wave.cs", "WaveTests.cs"})

    def test_token_estimate_is_positive(self):
        self.assertGreater(estimate_tokens("한글 and English"), 0)

    def test_sensitive_files_are_excluded(self):
        self.assertFalse(is_text_file(Path(".env")))
        self.assertFalse(is_text_file(Path("settings.local.json")))
        self.assertFalse(is_text_file(Path("private.key")))

    def test_config_loads_json_object(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".localassistant.json").write_text('{"max_files": 4}', encoding="utf-8")
            self.assertEqual(load_config(root)["max_files"], 4)

    def test_cache_key_changes_when_source_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "a.py"
            first = type("Item", (), {"relative": "a.py", "text": "one"})()
            second = type("Item", (), {"relative": "a.py", "text": "two"})()
            self.assertNotEqual(cache_key("q", "m", [first]), cache_key("q", "m", [second]))


if __name__ == "__main__":
    unittest.main()
