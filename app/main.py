from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.admin import router as admin_page_router
from app.api.admin import router as admin_api_router
from app.api.public import router as public_router
from app.core.config import settings
from app.db.session import check_database_connection
from app.api.public import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_database_connection()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:5500",
        "https://digitalassetkoreasummit.com",
        "https://www.digitalassetkoreasummit.com",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount(
    "/admin/static",
    StaticFiles(directory="app/admin/static"),
    name="admin-static",
)
# app.include_router(webhook_router)
# app.include_router(public_router)
app.include_router(admin_api_router)
app.include_router(admin_page_router)
app.include_router(public_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "environment": settings.app_env,
    }