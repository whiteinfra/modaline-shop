import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from . import __version__
from .config import settings
from .routers import auth, customers, orders, payments, products, stats

SWAGGER_UI_DIR = os.getenv("SWAGGER_UI_DIR")  # офлайн-ресурси Swagger UI (необов'язково)

app = FastAPI(
    docs_url=None if SWAGGER_UI_DIR else "/docs",
    title="ModaLine Shop API",
    version=__version__,
    description="REST API інтернет-магазину одягу «ModaLine»: товари, клієнти, замовлення, платежі. "
    "Автентифікація — JWT (кнопка **Authorize**: email і пароль співробітника).",
    openapi_tags=[
        {"name": "Автентифікація"},
        {"name": "Товари"},
        {"name": "Клієнти"},
        {"name": "Замовлення"},
        {"name": "Платежі"},
        {"name": "Статистика"},
    ],
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

for r in (auth.router, products.router, customers.router, orders.router, payments.router, stats.router):
    app.include_router(r, prefix="/api")


if SWAGGER_UI_DIR:
    app.mount("/swagger-assets", StaticFiles(directory=SWAGGER_UI_DIR), name="swagger-assets")

    @app.get("/docs", include_in_schema=False)
    def offline_docs():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="ModaLine Shop API — Swagger UI",
            swagger_js_url="/swagger-assets/swagger-ui-bundle.js",
            swagger_css_url="/swagger-assets/swagger-ui.css",
            swagger_favicon_url="/swagger-assets/favicon-32x32.png",
        )


@app.exception_handler(IntegrityError)
def integrity_error(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409, content={"detail": "Порушення цілісності даних: " + str(exc.orig).split("\n")[0]}
    )


@app.get("/api/health", tags=["Статистика"], summary="Перевірка стану сервісу")
def health():
    return {"status": "ok", "version": __version__}


if os.path.isdir(settings.frontend_dir):
    app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
