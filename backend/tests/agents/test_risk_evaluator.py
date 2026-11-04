from app.agents.remediation.risk_evaluator import PatchRiskEvaluator
from app.agents.schemas.remediation import (
    PatchRiskLevel,
    PatchValidationResult,
    ProposedPatch,
)


def test_risk_evaluator_low_risk():
    patch = ProposedPatch(
        title="Fix null check in helper",
        problem_description="NoneType error on missing key",
        technical_rationale="Add defensive check",
        files_affected=["src/utils/formatters.py"],
        diff_content="--- a/src/utils/formatters.py\n+++ b/src/utils/formatters.py\n@@ -1,1 +1,2 @@\n+if not x: return ''\n",
        expected_outcome="No NoneType errors",
        risk_level=PatchRiskLevel.LOW,
    )
    val = PatchValidationResult(
        is_valid=True,
        syntax_valid=True,
        authorized_files_only=True,
        lines_added=2,
        lines_removed=0,
    )

    assessment = PatchRiskEvaluator.evaluate(patch, val)
    assert assessment.risk_level == PatchRiskLevel.LOW
    assert assessment.risk_score <= 0.30
    assert assessment.rollback_complexity == "LOW"


def test_risk_evaluator_destructive_operations_critical():
    """Verify destructive operations (DROP TABLE, os.remove) force CRITICAL risk."""
    destructive_diff = """--- a/src/db/cleanup.py
+++ b/src/db/cleanup.py
@@ -1,2 +1,3 @@
 def purge():
+    DROP TABLE users;
     pass
"""
    patch = ProposedPatch(
        title="Purge users",
        problem_description="Cleanup task",
        technical_rationale="Purge table",
        files_affected=["src/db/cleanup.py"],
        diff_content=destructive_diff,
        expected_outcome="Users purged",
        risk_level=PatchRiskLevel.LOW,  # LLM tries to claim LOW risk
    )
    val = PatchValidationResult(
        is_valid=True,
        syntax_valid=True,
        authorized_files_only=True,
        lines_added=1,
        lines_removed=0,
    )

    assessment = PatchRiskEvaluator.evaluate(patch, val)
    assert assessment.risk_level == PatchRiskLevel.CRITICAL
    assert assessment.risk_score == 1.0
    assert any("Destructive operation detected" in f for f in assessment.risk_factors)


def test_risk_evaluator_llm_cannot_downgrade_sensitive_subsystems():
    """Verify LLM cannot downgrade risk when authentication, payment, or crypto files are modified."""
    # Test Auth / Crypto
    patch = ProposedPatch(
        title="Update jwt token verification",
        problem_description="Token expiration logic",
        technical_rationale="Use hashlib sha256 with secret_key",
        files_affected=["src/auth/token_service.py"],
        diff_content="--- a/src/auth/token_service.py\n+++ b/src/auth/token_service.py\n@@ -1,1 +1,2 @@\n+encrypt\n",
        expected_outcome="Verified tokens",
        risk_level=PatchRiskLevel.LOW,  # Model claims LOW
    )
    val = PatchValidationResult(
        is_valid=True,
        syntax_valid=True,
        authorized_files_only=True,
        lines_added=5,
        lines_removed=1,
    )

    assessment = PatchRiskEvaluator.evaluate(patch, val)
    # Must be escalated to at least HIGH due to auth and crypto
    assert assessment.risk_level in (PatchRiskLevel.HIGH, PatchRiskLevel.CRITICAL)
    assert any("escalated risk from LOW to" in f for f in assessment.risk_factors)


def test_risk_evaluator_payment_and_database_migration():
    """Verify payment and migration files elevate risk to HIGH."""
    patch = ProposedPatch(
        title="Alter billing invoice schema",
        problem_description="Add charge status",
        technical_rationale="Database migration for payment checkout",
        files_affected=["src/db/alembic/versions/migration_charge.py"],
        diff_content="--- a/src/db/alembic/versions/migration_charge.py\n+++ b/src/db/alembic/versions/migration_charge.py\n@@ -1,1 +1,2 @@\n+add column\n",
        expected_outcome="Updated invoice schema",
        risk_level=PatchRiskLevel.MEDIUM,
    )
    val = PatchValidationResult(
        is_valid=True,
        syntax_valid=True,
        authorized_files_only=True,
        lines_added=4,
        lines_removed=0,
    )

    assessment = PatchRiskEvaluator.evaluate(patch, val)
    assert assessment.risk_level in (PatchRiskLevel.HIGH, PatchRiskLevel.CRITICAL)
    assert any("Database Migration" in f for f in assessment.risk_factors)
