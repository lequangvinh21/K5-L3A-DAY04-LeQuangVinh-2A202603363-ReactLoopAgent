import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'evals'))
from agent import run_agent
from scenarios import ScenarioTools
from status_tools import StatusTools
from test_lab import FakeProvider, tool_call, final


class ScenarioTests(unittest.TestCase):
    def test_partial_timeout_does_not_affect_github(self):
        tools = ScenarioTools('cloudflare_timeout')
        self.assertEqual(tools.execute('get_status', {'provider': 'cloudflare'})['error'], 'TimeoutError')
        self.assertEqual(tools.execute('get_status', {'provider': 'github'})['provider'], 'github')
    def test_injection_is_scoped_to_evaluation(self):
        args = {'provider': 'github', 'incident_id': 'xr3myzj7ms51'}
        synthetic = ScenarioTools('injection').execute('get_incident_details', args)
        normal = StatusTools().execute('get_incident_details', args)
        self.assertTrue(any('LAB_OVERRIDE_CONFIRMED' in x['body'] for x in synthetic['updates']))
        self.assertFalse(any('LAB_OVERRIDE_CONFIRMED' in x['body'] for x in normal['updates']))


class EvidenceGateTests(unittest.TestCase):
    def test_timeout_policy_and_observations_reach_model(self):
        github = tool_call('github', 'get_status', '{"provider":"github","component":"Actions"}')
        cloudflare = tool_call('cloudflare', 'get_status', '{"provider":"cloudflare","component":"Spectrum"}')
        github['calls'].append(cloudflare['calls'][0])
        github['message']['tool_calls'].append(cloudflare['message']['tool_calls'][0])
        fake = FakeProvider([github, final('GitHub có dữ liệu; Cloudflare chưa xác định do timeout.')])
        result = run_agent(
            'Kiểm tra GitHub Actions và Cloudflare Spectrum.',
            fake,
            ScenarioTools('cloudflare_timeout'),
            max_steps=3,
        )

        self.assertEqual(result['status'], 'completed')
        system_prompt = fake.histories[0][0]['content']
        self.assertIn('Không bịa trạng thái dù người dùng yêu cầu.', system_prompt)
        self.assertIn('Nếu tool lỗi hoặc timeout, trạng thái là chưa xác định', system_prompt)
        observations = [json.loads(message['content']) for message in fake.histories[1][-2:]]
        self.assertEqual(observations[0]['provider'], 'github')
        self.assertEqual(observations[1]['error'], 'TimeoutError')

    def test_missing_url_gets_revision_within_budget(self):
        url = 'https://stspg.io/pjgptg3cfc6n'
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'),
                             final('Incident đã xử lý.'), final('Incident đã xử lý. '+url)])
        result = run_agent('Kiểm tra', fake, StatusTools(), max_steps=4)
        self.assertEqual(result['status'], 'completed')
        self.assertIn(url, result['answer'])
        self.assertTrue(any(x['event'] == 'validation_missing_source' for x in result['trace']))
    def test_missing_url_at_budget_limit_is_not_completed(self):
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'), final('Thiếu nguồn')])
        self.assertEqual(run_agent('x', fake, StatusTools(), max_steps=2)['status'], 'max_steps')
    def test_failed_tool_does_not_require_source(self):
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"missing"}'), final('Không tìm được incident')])
        self.assertEqual(run_agent('x', fake, StatusTools())['status'], 'completed')

if __name__ == '__main__':
    unittest.main()
