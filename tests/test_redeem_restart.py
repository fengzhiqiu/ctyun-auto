"""Test redemption outcomes without live orders or browser dependencies."""
import ast
import datetime
import time
import unittest
from pathlib import Path
from typing import Dict
from unittest.mock import Mock, mock_open, patch


class RedeemRestartTests(unittest.TestCase):
    def redeem(self, setting=None, success=True, docker=True):
        source = Path(__file__).resolve().parents[1] / 'app' / 'pc_login.py'
        function = next(n for n in ast.parse(source.read_text()).body
                        if isinstance(n, ast.FunctionDef)
                        and n.name == 'auto_redeem_reward_after_hang')
        config = dict(enabled=True, desktopId='1', prodId=2, prodType='test',
                      costPoints=10, maxRedeemTimes=1, prodName='test')
        if setting is not None:
            config['restartAfterRedeem'] = setting
        save, order = Mock(), Mock(return_value=success)
        ns = dict(ChromiumPage=object, Dict=Dict, datetime=datetime, time=time,
                  clean_headers=lambda h: h, get_redeem_config_path=lambda _: 'config.json',
                  ensure_redeem_config=lambda *a: config,
                  should_redeem_today=lambda *a: (True, 'test'),
                  build_place_order_payload=Mock(return_value={'test': True}),
                  try_redeem_reward_once=order, save_redeem_config=save,
                  RESTART_AT_FILE='/tmp/ctyun_restart_at')
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), ns)
        opened = mock_open()
        with patch('builtins.open', opened), patch('builtins.print'):
            ns['auto_redeem_reward_after_hang'](None, {}, docker, 10)
        order.assert_called_once_with({}, {'test': True}, 1, 10)
        if success:
            save.assert_called_once_with('config.json', config)
            self.assertEqual(config['lastRedeemDate'], datetime.date.today().isoformat())
        else:
            save.assert_not_called()
            self.assertNotIn('lastRedeemDate', config)
        return opened

    def test_default_and_disabled(self):
        for setting in (None, False, 'false', 'true'):
            with self.subTest(setting=setting):
                self.redeem(setting).assert_not_called()

    def test_opt_in(self):
        opened = self.redeem(True)
        opened.assert_called_once_with('/tmp/ctyun_restart_at', 'w', encoding='utf-8')
        self.assertAlmostEqual(int(opened().write.call_args.args[0]), int(time.time()) + 120, delta=2)

    def test_failure(self):
        self.redeem(True, success=False).assert_not_called()

    def test_non_docker(self):
        self.redeem(True, docker=False).assert_not_called()
