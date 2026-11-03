from logging.config import fileConfig

from alembic import context

import app.db.models  # noqa: F401  registers the tables on Base.metadata
from app.db.session import Base, get_engine

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name, disable_existing_loggers=False)


def run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


# Tests pass their own connection; otherwise connect to DATABASE_URL.
if (connection := context.config.attributes.get("connection")) is not None:
    run_migrations(connection)
else:
    with get_engine().connect() as connection:
        run_migrations(connection)
