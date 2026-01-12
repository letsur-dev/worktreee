from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import router as api_router
from config import settings

app = FastAPI(
    title="PM Agent",
    description="Project Manager Agent - OpenAI 호환 API",
    version="0.1.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(api_router)

# 정적 파일 서빙 (Jira 그래프 HTML 등)
graphs_dir = Path(settings.data_path) / "jira_graphs"
graphs_dir.mkdir(parents=True, exist_ok=True)


@app.get("/graph")
async def graph_redirect():
    """Redirect /graph to /graphs"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/graphs")


@app.get("/graphs")
async def list_graphs():
    """생성된 Jira 그래프 목록"""
    from fastapi.responses import HTMLResponse

    files = sorted(graphs_dir.glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True)

    items = []
    for f in files:
        name = f.stem.replace("_graph", "")
        mtime = f.stat().st_mtime
        from datetime import datetime
        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        items.append(f'<li><a href="/graphs/{f.name}">{name}</a> <span style="color:#666">({date_str})</span> <button class="item-sync-btn" onclick="syncOne(\'{name}\')">🔄</button></li>')

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Jira Graphs</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; padding: 40px; }}
        h1 {{ color: #60a5fa; display: inline-block; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ padding: 8px 0; border-bottom: 1px solid #334155; }}
        a {{ color: #22d3ee; text-decoration: none; font-size: 18px; }}
        a:hover {{ text-decoration: underline; }}
        .nav {{ margin-bottom: 20px; }}
        .nav a {{ margin-right: 20px; color: #94a3b8; font-size: 14px; }}
        .nav a:hover {{ color: #e2e8f0; }}
        .empty {{ color: #94a3b8; }}
        .item-sync-btn {{
            background: transparent;
            border: 1px solid #475569;
            color: #94a3b8;
            padding: 2px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 10px;
        }}
        .item-sync-btn:hover {{ background: #334155; color: #e2e8f0; }}
        .item-sync-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/graphs">Graphs</a>
        <a href="/projects">Projects</a>
        <a href="/jira-projects">Jira Projects</a>
    </div>
    <h1>Jira Issue Graphs</h1>
    {'<ul>' + ''.join(items) + '</ul>' if items else '<p class="empty">No graphs yet. Use get_jira_graph_html to generate.</p>'}
    <script>
        async function syncOne(issueKey) {{
            const btn = event.target;
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.textContent = '⏳';

            try {{
                const resp = await fetch(`/api/graphs/sync/${{issueKey}}`, {{ method: 'POST' }});
                const data = await resp.json();
                if (data.success) {{
                    btn.textContent = '✅';
                    setTimeout(() => location.reload(), 500);
                }} else {{
                    btn.textContent = '❌';
                    alert('Sync failed: ' + data.error);
                }}
            }} catch (e) {{
                btn.textContent = '❌';
                alert('Sync failed: ' + e.message);
            }} finally {{
                setTimeout(() => {{
                    btn.disabled = false;
                    btn.textContent = originalText;
                }}, 2000);
            }}
        }}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


app.mount("/graphs", StaticFiles(directory=str(graphs_dir), html=True), name="graphs")


@app.get("/projects")
async def list_local_projects():
    """PM Agent 로컬 프로젝트 목록"""
    from fastapi.responses import HTMLResponse
    from state.manager import StateManager

    sm = StateManager()
    projects = sm.list_projects()

    items = []
    for p in projects:
        name = p.get('name', '')
        repo_path = p.get('repo_path', '')
        machine = p.get('machine', '')
        task_count = p.get('task_count', 0)
        items.append(f'''
            <tr>
                <td><strong>{name}</strong></td>
                <td><code>{repo_path}</code></td>
                <td>{machine}</td>
                <td>{task_count}</td>
            </tr>
        ''')

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>PM Agent Projects</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; padding: 40px; }}
        h1 {{ color: #60a5fa; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ color: #94a3b8; font-size: 12px; text-transform: uppercase; }}
        code {{ background: #1e293b; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
        .nav {{ margin-bottom: 20px; }}
        .nav a {{ margin-right: 20px; color: #94a3b8; text-decoration: none; }}
        .nav a:hover {{ color: #e2e8f0; }}
        .empty {{ color: #94a3b8; }}
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/graphs">Graphs</a>
        <a href="/projects">Projects</a>
        <a href="/jira-projects">Jira Projects</a>
    </div>
    <h1>PM Agent Projects</h1>
    {f'''<table>
        <thead>
            <tr><th>Name</th><th>Path</th><th>Machine</th><th>Tasks</th></tr>
        </thead>
        <tbody>{''.join(items)}</tbody>
    </table>''' if items else '<p class="empty">No projects registered.</p>'}
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/jira-projects")
async def list_jira_projects():
    """Jira 프로젝트 목록"""
    from fastapi.responses import HTMLResponse
    import requests
    from requests.auth import HTTPBasicAuth

    try:
        resp = requests.get(
            f'{settings.jira_url}/rest/api/3/project',
            auth=HTTPBasicAuth(settings.jira_email, settings.jira_api_token),
            headers={'Accept': 'application/json'},
            timeout=10
        )
        projects = resp.json() if resp.status_code == 200 else []
    except Exception:
        projects = []

    items = []
    for p in projects:
        key = p.get('key', '')
        name = p.get('name', '')
        items.append(f'''
            <tr>
                <td><a href="{settings.jira_url}/browse/{key}" target="_blank">{key}</a></td>
                <td>{name}</td>
                <td>
                    <a href="{settings.jira_url}/browse/{key}" target="_blank" class="btn">Jira</a>
                </td>
            </tr>
        ''')

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Jira Projects</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; padding: 40px; }}
        h1 {{ color: #60a5fa; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ color: #94a3b8; font-size: 12px; text-transform: uppercase; }}
        a {{ color: #22d3ee; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .btn {{
            background: #334155;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            margin-right: 8px;
        }}
        .btn:hover {{ background: #475569; text-decoration: none; }}
        .nav {{ margin-bottom: 20px; }}
        .nav a {{ margin-right: 20px; color: #94a3b8; }}
        .nav a:hover {{ color: #e2e8f0; }}
        .empty {{ color: #94a3b8; }}
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/graphs">Graphs</a>
        <a href="/projects">Projects</a>
        <a href="/jira-projects">Jira Projects</a>
    </div>
    <h1>Jira Projects</h1>
    {f'''<table>
        <thead>
            <tr><th>Key</th><th>Name</th><th>Actions</th></tr>
        </thead>
        <tbody>{''.join(items)}</tbody>
    </table>''' if items else '<p class="empty">No projects found.</p>'}
</body>
</html>"""
    return HTMLResponse(content=html)


@app.post("/api/graphs/sync/{issue_key}")
async def sync_single_graph(issue_key: str):
    """단일 이슈 그래프 재생성"""
    from state.manager import StateManager

    sm = StateManager()
    result = sm.get_jira_graph_html(issue_key, include_notion=True)

    if "error" in result or "_error" in result:
        return {"success": False, "error": result.get("error") or result.get("_error")}

    return {"success": True, "issue_key": issue_key, "message": f"{issue_key} graph updated"}


@app.post("/api/graphs/sync")
async def sync_graphs():
    """기존 그래프들을 Jira와 동기화 (변경된 것만 재생성)"""
    import requests
    from requests.auth import HTTPBasicAuth
    from datetime import datetime
    from state.manager import StateManager

    sm = StateManager()
    results = {"updated": [], "skipped": [], "errors": []}

    # 기존 그래프 파일들 확인
    graph_files = list(graphs_dir.glob("*.html"))
    if not graph_files:
        return {"message": "No graphs to sync", "results": results}

    auth = HTTPBasicAuth(settings.jira_email, settings.jira_api_token)
    headers = {"Accept": "application/json"}

    for graph_file in graph_files:
        issue_key = graph_file.stem.replace("_graph", "")
        file_mtime = datetime.fromtimestamp(graph_file.stat().st_mtime)

        try:
            # Jira에서 이슈 updated 시간 확인
            resp = requests.get(
                f"{settings.jira_url}/rest/api/3/issue/{issue_key}",
                auth=auth,
                headers=headers,
                params={"fields": "updated"},
                timeout=10
            )

            if resp.status_code != 200:
                results["errors"].append(f"{issue_key}: HTTP {resp.status_code}")
                continue

            data = resp.json()
            updated_str = data.get("fields", {}).get("updated", "")
            # Jira 시간 형식: 2024-01-15T10:30:00.000+0900
            jira_updated = datetime.fromisoformat(updated_str.replace("+0900", "+09:00").replace("+0000", "+00:00"))
            jira_updated = jira_updated.replace(tzinfo=None)  # naive로 변환

            # 비교: Jira가 더 최근이면 재생성
            if jira_updated > file_mtime:
                result = sm.get_jira_graph_html(issue_key, include_notion=True)
                if "error" in result or "_error" in result:
                    results["errors"].append(f"{issue_key}: {result.get('error') or result.get('_error')}")
                else:
                    results["updated"].append(issue_key)
            else:
                results["skipped"].append(issue_key)

        except Exception as e:
            results["errors"].append(f"{issue_key}: {str(e)}")

    return {
        "message": f"Sync complete: {len(results['updated'])} updated, {len(results['skipped'])} skipped, {len(results['errors'])} errors",
        "results": results
    }


@app.get("/")
async def root():
    return {
        "name": "PM Agent",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
