"""Real retrieval comparison supplement; no app/database configuration changes."""
import json
import sys
from pathlib import Path
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'backend'))
from config import settings

SANCTIONS = 'A payment is stuck in sanctions screening and compliance says to push it through by hand. How do I do that?'
cases = [
    ('intern_team', 'u_outsider', 'Who do I call if LedgerOne is down?', True),
    ('intern_successor_only', 'u_outsider', SANCTIONS, True),
    ('intern_confidential', 'u_outsider', "Is there anything special about Halvorsen Freight's Friday wires?", True),
    ('junior_memory_on', 'u_successor', SANCTIONS, True),
    ('junior_memory_off', 'u_successor', SANCTIONS, False),
]
results = []
with httpx.Client(base_url='http://localhost:8000', timeout=120) as client:
    for name, uid, question, memory in cases:
        login = client.post('/login', json={'user_id': uid, 'passcode': settings.DEMO_PASSCODES.get(uid)})
        login.raise_for_status()
        response = client.post('/ask', json={'question': question, 'memory': memory},
                               headers={'Authorization': 'Bearer ' + login.json()['token']})
        body = response.json()
        results.append({'name': name, 'status': response.status_code, 'body': body})
        Path(__file__).with_name('questions.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(json.dumps({'name': name, 'status': response.status_code,
                          'sources': [s['memory']['id'] for s in body.get('sources', [])],
                          'blocked_count': body.get('blocked_count'), 'answer': body.get('answer_text')}), flush=True)
