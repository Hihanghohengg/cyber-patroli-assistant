import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

logger = logging.getLogger("app.database")


def _init_engine():
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    if "postgresql" in db_url:
        try:
            test_engine = create_engine(
                db_url,
                echo=False,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 3},
            )
            with test_engine.connect() as conn:
                logger.info("Connected to PostgreSQL database successfully.")
                return test_engine
        except Exception as e:
            logger.warning(
                "PostgreSQL connection to %s failed (%s). Falling back to persistent SQLite.",
                db_url.split("@")[-1] if "@" in db_url else db_url,
                e,
            )

    os.makedirs("storage", exist_ok=True)
    sqlite_file = os.path.abspath(os.path.join("storage", "patrol.db")).replace("\\", "/")
    logger.info("Using SQLite database: sqlite:///%s", sqlite_file)
    return create_engine(
        f"sqlite:///{sqlite_file}",
        connect_args={"check_same_thread": False},
        echo=False,
    )


engine = _init_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"

try:
    from pgvector.sqlalchemy import Vector
    @compiles(Vector, "sqlite")
    def compile_vector_sqlite(type_, compiler, **kw):
        return "TEXT"
except Exception:
    pass

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables defined by SQLAlchemy models and ensure admin is seeded."""
    import app.models.report  # noqa: F401
    import app.models.evidence  # noqa: F401
    import app.models.user  # noqa: F401
    import app.models.audit  # noqa: F401
    import app.models.intelligence  # noqa: F401
    import app.models.entities  # noqa: F401
    import app.models.knowledge  # noqa: F401
    Base.metadata.create_all(bind=engine)

    try:
        from app.auth.dependencies import seed_default_admin_if_needed
        from app.services.seeder import seed_proposal_data_if_needed
        with SessionLocal() as db:
            seed_default_admin_if_needed(db)
            seed_proposal_data_if_needed(db)
    except Exception as e:
        logger.warning("Could not run database seeders on init_db: %s", e)
