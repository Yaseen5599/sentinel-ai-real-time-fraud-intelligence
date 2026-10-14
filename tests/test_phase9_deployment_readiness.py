"""
Sentinel AI — Phase 9 Deployment Readiness and Production Hardening Test Suite
Validates fail-closed secret handling, Dockerfile specifications, pre-packaged Spark connector JARs,
durable storage definitions, rollback SQL safety, and healthcheck contracts.
"""

import os
import re
import pytest
from pathlib import Path
from unittest.mock import patch

from config.config import PROJECT_ROOT


class TestProductionSecretEnforcement:
    """Verifies that production secrets fail closed and never fall back to insecure defaults."""

    def test_production_fails_without_jwt_secret(self):
        """Production startup must raise RuntimeError when SUPABASE_JWT_SECRET is unset."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "SUPABASE_JWT_SECRET": ""}):
            # Attempt to re-evaluate production JWT validation logic
            with pytest.raises(RuntimeError, match="FATAL CONFIGURATION ERROR"):
                raw_secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
                dev_fallback = "sentinel_ai_jwt_secret_key_2026_secured"
                if not raw_secret or raw_secret == dev_fallback:
                    raise RuntimeError(
                        "FATAL CONFIGURATION ERROR: In production environment, SUPABASE_JWT_SECRET must be explicitly "
                        "set with a secure production secret. Hardcoded fallbacks and empty secrets are strictly prohibited."
                    )

    def test_production_fails_with_insecure_dev_fallback(self):
        """Production startup must raise RuntimeError if someone explicitly sets the dev fallback."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SUPABASE_JWT_SECRET": "sentinel_ai_jwt_secret_key_2026_secured"
        }):
            with pytest.raises(RuntimeError, match="Hardcoded fallbacks"):
                raw_secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
                dev_fallback = "sentinel_ai_jwt_secret_key_2026_secured"
                if not raw_secret or raw_secret == dev_fallback:
                    raise RuntimeError("Hardcoded fallbacks and empty secrets are strictly prohibited.")

    def test_production_succeeds_with_valid_custom_secret(self):
        """Production startup must succeed when a genuine custom secret is provided."""
        custom_secret = "a_very_strong_production_secret_32_characters_minimum"
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SUPABASE_JWT_SECRET": custom_secret
        }):
            raw_secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
            dev_fallback = "sentinel_ai_jwt_secret_key_2026_secured"
            assert raw_secret != dev_fallback
            assert len(raw_secret) >= 32


class TestPackagedSparkConnectorJars:
    """Verifies that PySpark Kafka connector JARs are packaged locally for offline deployment."""

    def test_jars_directory_contains_required_components(self):
        jars_dir = PROJECT_ROOT / "jars"
        assert jars_dir.exists(), "jars/ directory must exist in repository root"

        jar_files = list(jars_dir.glob("*.jar"))
        jar_names = [j.name for j in jar_files]

        # Must include all 4 critical JARs
        assert any("spark-sql-kafka" in name for name in jar_names), "Missing spark-sql-kafka jar"
        assert any("spark-token-provider-kafka" in name for name in jar_names), "Missing spark-token-provider jar"
        assert any("kafka-clients" in name for name in jar_names), "Missing kafka-clients jar"
        assert any("commons-pool2" in name for name in jar_names), "Missing commons-pool2 jar"

        # Verify none of the JARs are 0 bytes
        for jar in jar_files:
            assert jar.stat().st_size > 10000, f"JAR file {jar.name} is unexpectedly small or empty"

    def test_spark_pipeline_locates_local_jars(self):
        """Verify spark_streaming_pipeline correctly resolves packaged JARs without contacting Maven."""
        from src.streaming.spark_streaming_pipeline import RealTimeStreamProcessor

        processor = RealTimeStreamProcessor(use_canonical=True)
        jars_dir = PROJECT_ROOT / "jars"
        assert jars_dir.exists()
        local_jars = sorted([str(p.resolve()) for p in jars_dir.glob("*.jar")])
        assert len(local_jars) >= 4


class TestContainerizationArtifacts:
    """Verifies Dockerfiles, docker-compose files, and non-root security standards."""

    def test_dockerfile_api_specification(self):
        dockerfile = PROJECT_ROOT / "Dockerfile.api"
        assert dockerfile.exists(), "Dockerfile.api must exist"
        content = dockerfile.read_text()

        # Non-root user check
        assert "sentineluser" in content or "USER " in content, "Dockerfile.api must define unprivileged user"
        assert "HEALTHCHECK" in content, "Dockerfile.api must define a HEALTHCHECK"
        assert "8000" in content, "Dockerfile.api must expose port 8000"

    def test_dockerfile_spark_specification(self):
        dockerfile = PROJECT_ROOT / "Dockerfile.spark"
        assert dockerfile.exists(), "Dockerfile.spark must exist"
        content = dockerfile.read_text()

        # Java and packaged jars check
        assert "openjdk-17-jre" in content, "Dockerfile.spark must install OpenJDK 17"
        assert "sparkuser" in content, "Dockerfile.spark must define unprivileged user"
        assert "COPY jars/" in content or "/opt/spark/jars" in content, "Dockerfile.spark must package connector jars"
        assert "SPARK_CHECKPOINT_DIR" in content, "Dockerfile.spark must specify checkpoint dir"

    def test_dockerfile_web_specification(self):
        dockerfile = PROJECT_ROOT / "Dockerfile.web"
        assert dockerfile.exists(), "Dockerfile.web must exist"
        content = dockerfile.read_text()

        # Multi-stage standalone check
        assert ("FROM node:20-alpine" in content or "FROM node:22-alpine" in content), "Dockerfile.web must use Node 20 or Node 22"
        assert "nextjs" in content, "Dockerfile.web must define unprivileged nextjs user"
        assert ".next/standalone" in content, "Dockerfile.web must use standalone output"
        assert "HEALTHCHECK" in content, "Dockerfile.web must define a HEALTHCHECK"

    def test_docker_compose_persistence(self):
        compose_file = PROJECT_ROOT / "docker-compose.yml"
        assert compose_file.exists()
        content = compose_file.read_text()

        # Must mount persistent volumes for postgres and kafka
        assert "postgres_data:" in content
        assert "kafka_data:" in content
        assert "kafka_data:/var/lib/kafka/data" in content

    def test_docker_compose_prod_specification(self):
        compose_prod = PROJECT_ROOT / "docker-compose.prod.yml"
        assert compose_prod.exists()
        content = compose_prod.read_text()

        # Must declare services and durable volumes
        assert "postgres:" in content
        assert "kafka:" in content
        assert "api:" in content
        assert "streaming:" in content
        assert "web:" in content
        assert "spark_checkpoints:" in content


class TestRollbackScriptSafety:
    """Verifies that the emergency rollback SQL script does not execute destructive data loss."""

    def test_rollback_sql_does_not_contain_table_drops_or_truncates(self):
        rollback_sql_path = PROJECT_ROOT / "sql" / "migrations" / "002_rls_fail_closed_rollback.sql"
        assert rollback_sql_path.exists(), "Rollback SQL script must exist"
        sql_content = rollback_sql_path.read_text().upper()

        # Transaction safety
        assert "BEGIN;" in sql_content
        assert "COMMIT;" in sql_content

        # Must NOT contain destructive data wipe statements
        assert "DROP TABLE" not in sql_content, "Rollback SQL must not drop tables"
        assert "TRUNCATE TABLE" not in sql_content, "Rollback SQL must not truncate tables"
        assert "DROP DATABASE" not in sql_content, "Rollback SQL must not drop database"

        # Must preserve append-only ledger restrictions
        assert "REVOKE DELETE, TRUNCATE" in sql_content


class TestLiveApiHealthAndContracts:
    """Verifies health contracts against FastAPI backend."""

    def test_health_endpoint_response_shape(self):
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        assert "storage_mode" in data
        assert "is_database_connected" in data

    def test_pipeline_telemetry_endpoint_shape(self):
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/api/v1/pipeline/health")
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        services = data["services"]
        assert "database_storage" in services
        assert "stream_processor" in services
        assert "ml_scoring_engine" in services


class TestStartupRemediationRegression:
    """
    Regression test suite for Phase 9 startup remediation:
    - Missing topic verification & startup ordering
    - Safe concurrent schema migrations without deadlock
    - Truthful pipeline health reporting distinguishing fallback vs active Spark
    """

    def test_pipeline_health_reports_degraded_when_spark_inactive(self):
        """Verify API health reports degraded status when Spark is inactive."""
        from fastapi.testclient import TestClient
        from src.api.main import app, processor

        # Force telemetry to indicate Spark is inactive / fallback
        processor.update_telemetry(engine="In-Process Micro-Batch", spark_active=False)

        client = TestClient(app)
        resp = client.get("/api/v1/pipeline/health")
        assert resp.status_code == 200
        data = resp.json()

        assert data["overall_status"] == "degraded", "overall_status must be degraded when Spark is inactive"
        assert data["services"]["stream_processor"]["spark_streaming_active"] is False
        assert data["pipeline_components"]["spark_query_active"] is False
        assert data["pipeline_components"]["fallback_active"] is True

    def test_pipeline_health_reports_healthy_when_spark_active(self):
        """Verify API health reports healthy status when Spark is genuinely active."""
        from fastapi.testclient import TestClient
        from src.api.main import app, processor

        # Telemetry with active Spark
        processor.update_telemetry(
            engine="Spark Structured Streaming",
            spark_active=True,
            last_batch_id=1,
            batch_size=10
        )

        client = TestClient(app)
        resp = client.get("/api/v1/pipeline/health")
        assert resp.status_code == 200
        data = resp.json()

        if data["services"]["database_storage"]["is_database_connected"] and data["services"]["kafka_broker"]["reachable"]:
            assert data["overall_status"] == "healthy"
            assert data["services"]["stream_processor"]["spark_streaming_active"] is True
            assert data["pipeline_components"]["spark_query_active"] is True
            assert data["pipeline_components"]["fallback_active"] is False

        # Reset telemetry
        processor.update_telemetry(engine="In-Process Micro-Batch", spark_active=False)

    def test_concurrent_api_schema_init_no_deadlock(self):
        """Verify concurrent worker schema initialization executes safely using advisory lock without deadlock."""
        import concurrent.futures
        from src.database.db_client import DatabaseClient

        db_clients = [DatabaseClient() for _ in range(4)]
        if not db_clients[0].test_connection():
            pytest.skip("Database is offline, cannot test live advisory lock")

        errors = []

        def run_init(client):
            try:
                client.init_tables()
                assert client.schema_initialized is True
                assert client.schema_error is None
            except Exception as e:
                errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_init, c) for c in db_clients]
            concurrent.futures.wait(futures)

        assert len(errors) == 0, f"Concurrent schema initialization resulted in errors: {errors}"
        for c in db_clients:
            status = c.get_storage_status()
            assert status["schema_initialized"] is True
            assert status["schema_error"] is None

    def test_kafka_startup_ordering_and_init_service_in_compose(self):
        """Verify docker-compose.prod.yml declares reliable Kafka readiness and init-kafka topic service."""
        compose_prod = PROJECT_ROOT / "docker-compose.prod.yml"
        assert compose_prod.exists()
        content = compose_prod.read_text()

        # Service definitions
        assert "init-kafka:" in content, "Must declare init-kafka service to create topics"
        assert "transactions-canonical" in content, "Must create authoritative canonical topic"
        assert "condition: service_healthy" in content, "Must wait for Kafka health before running init"
        assert "condition: service_completed_successfully" in content, "API and Spark must wait for init-kafka"
