from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.admin import router as admin_page_router
from app.api.admin import router as admin_api_router
from app.api.public import router as public_router
from app.core.config import settings
from app.db.session import check_database_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_database_connection()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.mount(
    "/admin/static",
    StaticFiles(directory="app/admin/static"),
    name="admin-static",
)

app.include_router(public_router)
app.include_router(admin_api_router)
app.include_router(admin_page_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "environment": settings.app_env,
    }