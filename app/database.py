import os
import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

logger = logging.getLogger("app.database")


def safe_json_loads(val):
    """Safely decode JSON values without raising JSONDecodeError on corrupted/legacy strings."""
    if val is None or val == "":
        return None
    if not isinstance(val, str):
        return val
    try:
        return json.loads(val)
    except Exception:
        return val


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
                json_deserializer=safe_json_loads,
            )
            with test_engine.connect():
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
        connect_args={"check_same_thread": False, "timeout": 60},
        echo=False,
        json_deserializer=safe_json_loads,
    )


engine = _init_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy import event

@event.listens_for(engine, "connect")
def configure_sqlite_connection(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=60000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
    except Exception as e:
        logger.debug("SQLite PRAGMA config skipped: %s", e)

@event.listens_for(engine, "handle_error")
def receive_handle_error(exception_context):
    logger.error("DB ERROR: %s", exception_context.original_exception)
    logger.error("STATEMENT: %s", exception_context.statement)
    logger.error("PARAMETERS: %s", exception_context.parameters)

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
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


def apply_schema_migrations(bind_engine):
    """Safely apply non-destructive schema migrations (add missing columns) to existing tables."""
    from sqlalchemy import inspect, text

    try:
        inspector = inspect(bind_engine)
        existing_tables = inspector.get_table_names()

        migrations = [
            ("evidences", "operator_id", "VARCHAR(100) DEFAULT 'OP-DEFAULT'"),
            ("evidences", "source_url", "TEXT"),
            ("evidences", "dom_text", "TEXT"),
            ("evidences", "ocr_text", "TEXT DEFAULT ''"),
            ("evidences", "captured_at_utc", "VARCHAR(50)"),
            ("evidences", "canonical_hash", "VARCHAR(64)"),
            ("evidences", "hmac_tag", "VARCHAR(64)"),
            ("evidences", "verification_status", "VARCHAR(50) DEFAULT 'VERIFIED'"),
            ("evidences", "last_verified_at", "DATETIME"),
            ("contents", "ocr_text", "TEXT DEFAULT ''"),
            ("reports", "operator_id", "VARCHAR(100) DEFAULT 'OP-DEFAULT'"),
            ("reports", "classification_mode", "VARCHAR(50) DEFAULT 'adaptive'"),
            ("reports", "is_potential_duplicate", "BOOLEAN DEFAULT 0"),
            ("reports", "duplicate_of_ticket", "VARCHAR(50)"),
            ("reports", "duplicate_similarity", "NUMERIC(4, 3)"),
            ("reports", "execution_latencies", "TEXT DEFAULT '{}'"),
            ("reports", "original_language", "VARCHAR(10) DEFAULT 'id'"),
            ("reports", "indonesian_content", "TEXT DEFAULT ''"),
            ("reports", "dalkonten_status", "VARCHAR(50) DEFAULT 'BELUM DITERUSKAN'"),
            ("reports", "dalkonten_forwarded_at", "DATETIME"),
            ("reports", "dalkonten_forwarded_by", "VARCHAR(100)"),
        ]

        with bind_engine.connect() as conn:
            for table, col, col_def in migrations:
                if table in existing_tables:
                    col_names = [c["name"] for c in inspector.get_columns(table)]
                    if col not in col_names:
                        try:
                            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
                            conn.commit()
                            logger.info("Migrated schema: Added column '%s' to table '%s'", col, table)
                        except Exception as e:
                            logger.warning("Could not add column '%s' to '%s': %s", col, table, e)
    except Exception as ex:
        logger.warning("Schema auto-migration check skipped or failed: %s", ex)


def init_db():
    """Create all tables defined by SQLAlchemy models and ensure admin is seeded."""
    import app.models.report
    import app.models.evidence
    import app.models.user
    import app.models.audit
    import app.models.intelligence
    import app.models.entities
    import app.models.knowledge
    import app.models.memory
    _ = (
        app.models.report,
        app.models.evidence,
        app.models.user,
        app.models.audit,
        app.models.intelligence,
        app.models.entities,
        app.models.knowledge,
        app.models.memory,
    )
    Base.metadata.create_all(bind=engine)
    apply_schema_migrations(engine)

    try:
        from app.auth.dependencies import seed_default_admin_if_needed
        from app.services.seeder import seed_proposal_data_if_needed
        with SessionLocal() as db:
            seed_default_admin_if_needed(db)
            if getattr(settings, "AUTO_SEED_PROPOSAL_DATA", False):
                seed_proposal_data_if_needed(db)
    except Exception as e:
        logger.warning("Could not run database seeders on init_db: %s", e)
