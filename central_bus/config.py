"""Central Bus v0.6 — Pydantic Settings & Configuration.

Loads from environment / .env with sensible defaults for development.
"""

from pydantic_settings import BaseSettings


class BusSettings(BaseSettings):
    """Settings for the Central Bus daemon."""

    # ── SQLite ────────────────────────────────────────────────────
    db_path: str = "central_bus/bus.db"

    # ── HTTP Server ───────────────────────────────────────────────
    host: str = "127.0.0.1"
    port: int = 8099

    # ── Logging ───────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── Queue ─────────────────────────────────────────────────────
    max_retries: int = 3

    # ── Backward compat toggle ────────────────────────────────────
    use_sqlite: bool = True

    model_config = {"env_prefix": "CENTRAL_BUS_", "env_file": ".env", "extra": "ignore"}


settings = BusSettings()
