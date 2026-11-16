"""Read-only readiness checks; credentials stay in memory and are never printed."""
import json
import sys
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from config import settings
import db

out = {'database': settings.MONGODB_DB, 'people': [], 'roles': {}}
out['people'] = [{k: p.get(k) for k in ('_id', 'name', 'role', 'team', 'successor_of')}
                 for p in db.col(db.PEOPLE).find({})]
with httpx.Client(base_url='http://localhost:8000', timeout=30) as client:
    out['health'] = client.get('/health').json()
    for uid in ('u_expert', 'u_successor', 'u_outsider'):
        login = client.post('/login', json={'user_id': uid, 'passcode': settings.DEMO_PASSCODES.get(uid)})
        login.raise_for_status()
        headers = {'Authorization': 'Bearer ' + login.json()['token']}
        role = {'identity': client.get('/me', headers=headers).json()}
        for route in ('memories', 'runbook', 'gaps'):
            response = client.get('/' + route, headers=headers)
            role[route] = {'status': response.status_code, 'ids': [x['id'] for x in response.json()]}
        audit = client.get('/audit', params={'limit': 200}, headers=headers).json()
        role['audit_actor_ids'] = sorted(set(a['actor_id'] for a in audit))
        role['audit_exposes_other_actors'] = any(a['actor_id'] != uid for a in audit)
        role['clip_status'] = {clip: client.get('/clips/' + clip, headers=headers).status_code
                               for clip in ('c_2', 'c_3', 'c_7')}
        out['roles'][uid] = role
    out['invalid_ask_status'] = client.post('/ask', json={'question': ''}, headers=headers).status_code
    out['invalid_scope_status'] = client.patch('/memories/m_8/scope', json={'scope': 'everyone'}, headers=headers).status_code
Path(__file__).with_name('readiness.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps({'health': out['health'], 'identities': [r['identity'] for r in out['roles'].values()],
                  'outsider_audit_actors': out['roles']['u_outsider']['audit_actor_ids']}))
