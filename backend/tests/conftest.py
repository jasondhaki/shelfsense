import os
import tempfile

# Tests never touch the network or the developer's real keys: environment variables override
# the .env file in pydantic-settings, and this runs before app.config caches settings.
os.environ.update(
    {
        "NOAA_ENABLED": "false",
        "VISION_MODE": "cached",
        "GEMINI_API_KEY": "",
        "GEMINI_VISION_MODEL": "",
        "GEMINI_EMBED_MODEL": "",
        "RAG_MODE": "bm25",
        "DATABASE_URL": "",
        "USERS_DB_PATH": os.path.join(tempfile.mkdtemp(), "users.db"),
        "AUTH_SECRET": "test-secret",
    }
)
