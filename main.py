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
    from datetime import datetime
    import requests
    from requests.auth import HTTPBasicAuth

    files = sorted(graphs_dir.glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True)

    # Jira에서 이슈 제목 가져오기
    issue_keys = [f.stem.replace("_graph", "") for f in files]
    titles = {}
    if issue_keys:
        try:
            jql = f"key in ({','.join(issue_keys)})"
            resp = requests.post(
                f"{settings.jira_url}/rest/api/3/search/jql",
                auth=HTTPBasicAuth(settings.jira_email, settings.jira_api_token),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                json={"jql": jql, "fields": ["summary"], "maxResults": 100},
                timeout=10
            )
            if resp.status_code == 200:
                for issue in resp.json().get("issues", []):
                    titles[issue["key"]] = issue["fields"]["summary"]
        except Exception:
            pass  # 실패해도 키만 표시

    items = []
    for f in files:
        key = f.stem.replace("_graph", "")
        title = titles.get(key, "")
        mtime = f.stat().st_mtime
        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        display = f"{key}: {title}" if title else key
        items.append(f'<li><a href="/graphs/{f.name}">{display}</a> <span style="color:#666">({date_str})</span> <button class="item-sync-btn" onclick="syncOne(\'{key}\')">Sync</button></li>')

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
        .sync-modal {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }}
        .sync-modal.active {{ display: flex; }}
        .sync-modal-content {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 24px;
            min-width: 400px;
            max-width: 600px;
            max-height: 70vh;
            overflow-y: auto;
        }}
        .sync-modal h3 {{
            color: #60a5fa;
            margin: 0 0 16px 0;
            font-size: 18px;
        }}
        .sync-log {{
            font-family: monospace;
            font-size: 13px;
            line-height: 1.6;
            color: #94a3b8;
        }}
        .sync-log .fetching {{ color: #fbbf24; }}
        .sync-log .fetched {{ color: #34d399; }}
        .sync-log .error {{ color: #f87171; }}
        .sync-log .done {{ color: #60a5fa; font-weight: bold; }}
        .sync-close {{
            margin-top: 16px;
            background: #334155;
            border: none;
            color: #e2e8f0;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
        }}
        .sync-close:hover {{ background: #475569; }}
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

    <div id="syncModal" class="sync-modal">
        <div class="sync-modal-content">
            <h3 id="syncTitle">Syncing...</h3>
            <div id="syncLog" class="sync-log"></div>
            <button id="syncClose" class="sync-close" style="display:none" onclick="closeModal()">Close</button>
        </div>
    </div>

    <script>
        const modal = document.getElementById('syncModal');
        const syncLog = document.getElementById('syncLog');
        const syncTitle = document.getElementById('syncTitle');
        const syncClose = document.getElementById('syncClose');
        let fetchedCount = 0;

        function closeModal() {{
            modal.classList.remove('active');
            location.reload();
        }}

        function syncOne(issueKey) {{
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = '...';

            // 모달 열기
            syncLog.innerHTML = '';
            syncTitle.textContent = `Syncing ${{issueKey}}...`;
            syncClose.style.display = 'none';
            fetchedCount = 0;
            modal.classList.add('active');

            // SSE 연결
            const es = new EventSource(`/api/graphs/sync-stream/${{issueKey}}`);

            es.onmessage = (e) => {{
                const data = JSON.parse(e.data);

                if (data.event === 'fetching') {{
                    syncLog.innerHTML += `<div class="fetching">  Fetching ${{data.key}}...</div>`;
                }} else if (data.event === 'fetched') {{
                    fetchedCount++;
                    const detail = data.detail ? `: ${{data.detail.substring(0, 40)}}` : '';
                    syncLog.innerHTML += `<div class="fetched">  ${{data.key}}${{detail}}</div>`;
                    syncTitle.textContent = `Syncing ${{issueKey}}... (${{fetchedCount}} issues)`;
                }} else if (data.event === 'done') {{
                    syncLog.innerHTML += `<div class="done">Sync complete! ${{fetchedCount}} issues synced.</div>`;
                    syncTitle.textContent = `Sync Complete`;
                    syncClose.style.display = 'block';
                    btn.textContent = 'Done';
                    btn.disabled = false;
                    es.close();
                }} else if (data.event === 'error') {{
                    syncLog.innerHTML += `<div class="error">Error: ${{data.detail}}</div>`;
                    syncTitle.textContent = `Sync Failed`;
                    syncClose.style.display = 'block';
                    btn.textContent = 'Error';
                    btn.disabled = false;
                    es.close();
                }}

                // 스크롤 맨 아래로
                syncLog.scrollTop = syncLog.scrollHeight;
            }};

            es.onerror = () => {{
                syncLog.innerHTML += `<div class="error">Connection lost</div>`;
                syncClose.style.display = 'block';
                btn.textContent = 'Sync';
                btn.disabled = false;
                es.close();
            }};
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
        title = p.get('title', '')
        repo_path = p.get('repo_path', '')
        machine = p.get('machine', '')
        task_count = p.get('task_count', 0)
        items.append(f'''
            <tr>
                <td><strong>{name}</strong></td>
                <td>{title}</td>
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
            <tr><th>Name</th><th>Title</th><th>Path</th><th>Machine</th><th>Tasks</th></tr>
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


@app.get("/api/graphs/sync-stream/{issue_key}")
async def sync_graph_stream(issue_key: str):
    """단일 이슈 그래프 재생성 (SSE 스트림)"""
    from fastapi.responses import StreamingResponse
    from state.manager import StateManager
    import json as json_module
    import queue
    import threading

    progress_queue = queue.Queue()

    def on_progress(event_type: str, key: str, detail: str | None):
        progress_queue.put({"event": event_type, "key": key, "detail": detail})

    def generate():
        sm = StateManager()

        # 별도 스레드에서 sync 실행
        result_holder = [None]
        def run_sync():
            result_holder[0] = sm.get_jira_graph_html(issue_key, include_notion=True, on_progress=on_progress)
            progress_queue.put(None)  # 종료 신호

        thread = threading.Thread(target=run_sync)
        thread.start()

        # 진행 상태 스트리밍
        while True:
            try:
                item = progress_queue.get(timeout=60)
                if item is None:
                    break
                yield f"data: {json_module.dumps(item, ensure_ascii=False)}\n\n"
            except queue.Empty:
                break

        thread.join()

        # 최종 결과
        result = result_holder[0]
        if result and ("error" in result or "_error" in result):
            yield f"data: {json_module.dumps({'event': 'error', 'detail': result.get('error') or result.get('_error')}, ensure_ascii=False)}\n\n"
        else:
            yield f"data: {json_module.dumps({'event': 'done', 'key': issue_key}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


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
