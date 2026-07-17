import urllib.request
import json

base_url = 'http://localhost:8000/api/v1'

def get_repos():
    req = urllib.request.Request(f'{base_url}/repositories', headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def rebuild_graph(repo_id):
    print(f'Rebuilding graph for {repo_id}...')
    req = urllib.request.Request(f'{base_url}/impact/rebuild?repo_id={repo_id}', method='POST', headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def analyze(repo_id, file_path):
    print(f'Analyzing {file_path}...')
    data = json.dumps({'repo_id': repo_id, 'file_path': file_path, 'algorithm': 'bfs'}).encode('utf-8')
    req = urllib.request.Request(f'{base_url}/impact/analyze', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

repos = get_repos()
if not repos:
    print('No repositories found!')
else:
    repo_id = repos[0]['id']
    try:
        rebuild_graph(repo_id)
        
        files = ['requests/api.py', 'requests/adapters.py', 'requests/auth.py', 'requests/sessions.py', 'requests/models.py', 'requests/utils.py']
        for f in files:
            res = analyze(repo_id, f)
            print(f'--- {f} ---')
            print(f'Affected files: {len(res.get("affected_files", []))}')
            print(f'Risk score: {res.get("risk_score", 0)}')
    except Exception as e:
        print('Error:', e)
