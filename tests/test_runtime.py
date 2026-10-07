import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from configure_runtime import configure, validate_cron


class RuntimeTests(unittest.TestCase):
    def test_cron_valid_ranges_and_lists(self):
        for expression in ("0 3,20 * * *", "0 4,6 * * *", "*/15 1-4 * 1,12 0-7"):
            self.assertEqual(validate_cron(expression), expression)

    def test_cron_rejects_commands_and_invalid_ranges(self):
        for expression in ("0 3 * * *\n* * * * * root evil",
                           "0 3 * * *;id", "60 0 * * *", "* 24 * * *",
                           "*/0 * * * *", "0 0 0 * *", "0 0 * 13 *",
                           "* * * * 8", "* * * *", "0 6-3 * * *"):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                validate_cron(expression)

    def test_environment_round_trip_and_device_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            env = {"APP_USER": "test-user", "APP_PASSWORD": "a'\"$ b\\c\nnext"}
            data, run, cron = base / "data", base / "run", base / "cron"
            first = configure(env, data, run, cron)
            self.assertTrue(first.startswith("web_"))
            self.assertEqual(first, configure(env, data, run, cron))
            stored = json.loads((run / "environment.json").read_text())
            self.assertEqual(stored["APP_PASSWORD"], env["APP_PASSWORD"])
            self.assertEqual(stored["DEVICECODE"], first)
            self.assertNotIn(env["APP_PASSWORD"], cron.read_text())
            self.assertEqual(cron.read_text().count(" root "), 2)
            self.assertEqual((run / "environment.json").stat().st_mode & 0o777, 0o600)
            env["DEVICECODE"] = "web_manual"
            self.assertEqual(configure(env, data, run, cron), "web_manual")
            del env["DEVICECODE"]
            self.assertEqual(configure(env, data, run, cron), "web_manual")

    def test_reject_missing_credentials_and_path_traversal(self):
        for env in ({}, {"APP_USER": "../bad", "APP_PASSWORD": "test"},
                    {"APP_USER": "test"}, {"APP_USER": "a\nb", "APP_PASSWORD": "test"}):
            with self.subTest(env=env), self.assertRaises(ValueError):
                configure(env)

    def test_redemption_config_is_persistent(self):
        # Load only the pure path helper, without browser/OCR dependencies.
        source = Path(__file__).resolve().parents[1] / "app" / "pc_login.py"
        function = next(node for node in ast.parse(source.read_text()).body
                        if isinstance(node, ast.FunctionDef)
                        and node.name == "get_redeem_config_path")
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
        self.assertEqual(namespace["get_redeem_config_path"](True), "/app/data/redeem_config.json")


if __name__ == "__main__":
    unittest.main()
