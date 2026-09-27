# CS 499 Enhancement:
# Centralizes environment-based database configuration in a dedicated
# module, separating configuration concerns from application logic and
# keeping sensitive database credentials out of the source code.

import os
from dotenv import load_dotenv

load_dotenv()

def get_env(name: str, default=None):
    """Retrieve an environment variable with an optional default value."""
    value = os.getenv(name, default)
    return value

DB_HOST = get_env("DB_HOST")
DB_PORT = get_env("DB_PORT", "5432")
DB_NAME = get_env("DB_NAME")
DB_USER = get_env("DB_USER")
DB_PASSWORD = get_env("DB_PASSWORD")