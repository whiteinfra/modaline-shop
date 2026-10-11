import os


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://shop:shop@localhost:5432/modaline_shop")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me-in-production-32b+")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    frontend_dir: str = os.getenv("FRONTEND_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))


settings = Settings()
