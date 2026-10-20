import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# 1. Add project root directory to Python path so 'app' can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
  sys.path.insert(0, project_root)

# 2. Import app configuration, base, and models for Alembic autogenerate
from app.core.config import settings
from app.database.base import Base
from app.models.category import Category
from app.models.product import Product
from app.models.supplier import Supplier

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
  fileConfig(config.config_file_name)

# 3. Override sqlalchemy.url dynamically using your MySQL credentials from .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 4. Set target metadata for model change detection
target_metadata = Base.metadata


def run_migrations_offline() -> None:
  """Run migrations in 'offline' mode."""
  url = config.get_main_option("sqlalchemy.url")
  context.configure(
      url=url,
      target_metadata=target_metadata,
      literal_binds=True,
      dialect_opts={"paramstyle": "named"},
  )

  with context.begin_transaction():
    context.run_migrations()


def run_migrations_online() -> None:
  """Run migrations in 'online' mode."""
  # FIXED: using config_ini_section instead of config_section_name
  connectable = engine_from_config(
      config.get_section(config.config_ini_section, {}),
      prefix="sqlalchemy.",
      poolclass=pool.NullPool,
  )

  with connectable.connect() as connection:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
      context.run_migrations()


if context.is_offline_mode():
  run_migrations_offline()
else:
  run_migrations_online()