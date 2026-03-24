"""Unit tests – application configuration"""
from app.core.config import settings
from app.core.executor_types import TOOLS_BY_OPTION


class TestConfig:
    def test_project_name(self):
        assert settings.PROJECT_NAME == "Red Team SaaS"

    def test_debug_flag(self):
        # In test env we force DEBUG=True
        assert settings.DEBUG is True

    def test_database_url_set(self):
        assert settings.DATABASE_URL is not None
        assert len(settings.DATABASE_URL) > 0

    def test_secret_key_set(self):
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) >= 10

    def test_algorithm_hs256(self):
        assert settings.ALGORITHM == "HS256"

    def test_access_token_expire_positive(self):
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0

    def test_refresh_token_expire_positive(self):
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS > 0

    def test_encryption_key_set(self):
        assert settings.ENCRYPTION_KEY is not None
        assert len(settings.ENCRYPTION_KEY) > 0

    def test_architecture_option_valid(self):
        assert settings.ARCHITECTURE_OPTION in ("A", "B", "C")

    def test_cors_origins_configured(self):
        assert isinstance(settings.BACKEND_CORS_ORIGINS, list)
        assert len(settings.BACKEND_CORS_ORIGINS) > 0

    def test_tool_execution_timeout_positive(self):
        assert settings.TOOL_EXECUTION_TIMEOUT > 0


class TestToolsMapping:
    def test_all_options_present(self):
        assert "A" in TOOLS_BY_OPTION
        assert "B" in TOOLS_BY_OPTION
        assert "C" in TOOLS_BY_OPTION

    def test_option_a_25_tools(self):
        assert TOOLS_BY_OPTION["A"]["total"] == 25

    def test_option_b_175_tools(self):
        assert TOOLS_BY_OPTION["B"]["total"] == 175

    def test_option_c_100_tools(self):
        assert TOOLS_BY_OPTION["C"]["total"] == 100

    def test_each_option_has_categories(self):
        for opt in ("A", "B", "C"):
            cats = TOOLS_BY_OPTION[opt].get("categories", {})
            assert len(cats) > 0, f"Option {opt} has no categories"

    def test_categories_counts_positive(self):
        for opt in ("A", "B", "C"):
            for cat, count in TOOLS_BY_OPTION[opt]["categories"].items():
                assert count > 0, f"Option {opt} category '{cat}' has 0 tools"
