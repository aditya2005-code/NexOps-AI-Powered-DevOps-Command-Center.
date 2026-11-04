import re
from typing import List, Set
from app.agents.schemas.remediation import (
    PatchRiskAssessment,
    PatchRiskLevel,
    PatchValidationResult,
    ProposedPatch,
)

LEVEL_ORDER = {
    PatchRiskLevel.LOW: 1,
    PatchRiskLevel.MEDIUM: 2,
    PatchRiskLevel.HIGH: 3,
    PatchRiskLevel.CRITICAL: 4,
}

# Domain-specific sensitive keyword clusters
AUTH_KEYWORDS = {"auth", "login", "oauth", "jwt", "token", "session", "password"}
AUTHZ_KEYWORDS = {"permission", "role", "rbac", "access_control", "authorize"}
CRYPTO_KEYWORDS = {"crypto", "cipher", "encrypt", "decrypt", "hashlib", "hmac", "secret_key", "private_key"}
PAYMENT_KEYWORDS = {"payment", "charge", "billing", "invoice", "credit_card", "stripe", "refund"}
MIGRATION_KEYWORDS = {"migration", "alembic", "schema", "alter table", "add column"}
CONFIG_KEYWORDS = {"settings.py", "config.py", "credentials", "secret"}

DESTRUCTIVE_PATTERN = re.compile(
    r"\b(drop\s+table|drop\s+database|delete\s+from|truncate\s+table|rm\s+-rf|os\.remove|os\.unlink|shutil\.rmtree)\b",
    re.IGNORECASE,
)


class PatchRiskEvaluator:
    """Evaluates stability and operational risk of a validated code patch with strict deterministic override."""

    @classmethod
    def evaluate(
        cls,
        patch: ProposedPatch,
        validation: PatchValidationResult,
    ) -> PatchRiskAssessment:
        risk_score = 0.1  # Baseline
        risk_factors: List[str] = []
        potential_side_effects: List[str] = list(patch.potential_side_effects)

        total_lines = validation.lines_added + validation.lines_removed
        diff_text = patch.diff_content or ""

        # 1. Destructive operations check (inspect lines being added in diff)
        added_lines = [l[1:] for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++")]
        added_text = "\n".join(added_lines)
        destructive_matches = DESTRUCTIVE_PATTERN.findall(added_text)
        if destructive_matches:
            risk_score = 1.0
            risk_factors.append(
                f"Destructive operation detected in patch: {', '.join(set(destructive_matches))}"
            )
            potential_side_effects.append("Data loss or irreversible database alteration.")

        # 2. Line change volume
        if total_lines > 150:
            risk_score += 0.35
            risk_factors.append(f"Large patch size ({total_lines} total lines changed).")
        elif total_lines > 50:
            risk_score += 0.20
            risk_factors.append(f"Moderate patch size ({total_lines} total lines changed).")

        # 3. Files count
        num_files = len(patch.files_affected)
        if num_files > 3:
            risk_score += 0.25
            risk_factors.append(f"Multi-file modification ({num_files} files touched).")
        elif num_files > 1:
            risk_score += 0.10
            risk_factors.append(f"{num_files} files modified across project.")

        # 4. High deletion ratio
        if validation.lines_removed > 30 and (validation.lines_removed / max(total_lines, 1)) > 0.75:
            risk_score += 0.20
            risk_factors.append("High ratio of deleted code (>75% deletions).")

        # 5. Sensitive domain keyword analysis across files and diff content
        all_text_lower = (
            " ".join(patch.files_affected).lower()
            + " "
            + diff_text.lower()
            + " "
            + patch.title.lower()
            + " "
            + patch.problem_description.lower()
        )

        detected_categories: Set[str] = set()

        if any(kw in all_text_lower for kw in AUTH_KEYWORDS):
            detected_categories.add("Authentication")
            risk_score += 0.25
        if any(kw in all_text_lower for kw in AUTHZ_KEYWORDS):
            detected_categories.add("Authorization / RBAC")
            risk_score += 0.25
        if any(kw in all_text_lower for kw in CRYPTO_KEYWORDS):
            detected_categories.add("Cryptography")
            risk_score += 0.30
        if any(kw in all_text_lower for kw in PAYMENT_KEYWORDS):
            detected_categories.add("Payment & Financial")
            risk_score += 0.30
        if any(kw in all_text_lower for kw in MIGRATION_KEYWORDS):
            detected_categories.add("Database Migration & Schema")
            risk_score += 0.35
        if any(kw in all_text_lower for kw in CONFIG_KEYWORDS):
            detected_categories.add("Sensitive Configuration")
            risk_score += 0.20

        if detected_categories:
            risk_factors.append(
                f"Modifies critical domain subsystems: {', '.join(sorted(detected_categories))}"
            )
            potential_side_effects.append(
                f"Regressions in {', '.join(sorted(detected_categories))} functionality."
            )

        # 6. Clamp deterministic score between 0.0 and 1.0
        final_score = round(min(max(risk_score, 0.0), 1.0), 2)

        # 7. Map score to deterministic risk level
        if final_score >= 0.70 or destructive_matches:
            det_level = PatchRiskLevel.CRITICAL
            rollback_complexity = "HIGH"
        elif final_score >= 0.45 or ("Database Migration & Schema" in detected_categories) or ("Payment & Financial" in detected_categories):
            det_level = PatchRiskLevel.HIGH
            rollback_complexity = "MEDIUM"
        elif final_score >= 0.25:
            det_level = PatchRiskLevel.MEDIUM
            rollback_complexity = "LOW"
        else:
            det_level = PatchRiskLevel.LOW
            rollback_complexity = "LOW"

        # 8. Deterministic override: LLM cannot downgrade deterministic risk!
        model_level = patch.risk_level or PatchRiskLevel.LOW
        final_level = max(det_level, model_level, key=lambda l: LEVEL_ORDER[l])

        if LEVEL_ORDER[det_level] > LEVEL_ORDER[model_level]:
            risk_factors.append(
                f"Deterministic risk policy escalated risk from {model_level.value} to {final_level.value}."
            )

        if not risk_factors:
            risk_factors.append("Minimal, focused single-file patch.")

        return PatchRiskAssessment(
            risk_level=final_level,
            risk_score=final_score,
            risk_factors=risk_factors,
            potential_side_effects=potential_side_effects,
            rollback_complexity=rollback_complexity,
        )
