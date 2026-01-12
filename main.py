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
        items.append(f'<li><a href="/graphs/{f.name}">{name}</a> <span style="color:#666">({date_str})</span></li>')

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Jira Graphs</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; padding: 40px; }}
        h1 {{ color: #60a5fa; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ padding: 8px 0; border-bottom: 1px solid #334155; }}
        a {{ color: #22d3ee; text-decoration: none; font-size: 18px; }}
        a:hover {{ text-decoration: underline; }}
        .empty {{ color: #94a3b8; }}
    </style>
</head>
<body>
    <h1>Jira Issue Graphs</h1>
    {'<ul>' + ''.join(items) + '</ul>' if items else '<p class="empty">No graphs yet. Use get_jira_graph_html to generate.</p>'}
</body>
</html>"""
    return HTMLResponse(content=html)


app.mount("/graphs", StaticFiles(directory=str(graphs_dir), html=True), name="graphs")


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
