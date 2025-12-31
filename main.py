from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
