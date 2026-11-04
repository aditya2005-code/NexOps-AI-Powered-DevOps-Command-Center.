import logging
from typing import Any, Dict, List
from app.agents.schemas.evidence import RootCauseHypothesis
from app.agents.state import InvestigationState

logger = logging.getLogger("nexops.agents.nodes.validate_hypotheses")


def validate_hypotheses_node(state: InvestigationState) -> Dict[str, Any]:
    """Node: Validates hypothesis evidence references, calculates calibrated confidence, and ranks hypotheses."""
    raw_result = state.get("investigation_result") or {}
    collected_ev = state.get("collected_evidence", [])
    valid_ev_ids = {ev.get("evidence_id") for ev in collected_ev if ev.get("evidence_id")}

    has_verified_evidence = any(ev.get("reliability") == "verified" for ev in collected_ev)
    is_insufficient = len(collected_ev) <= 1 and not has_verified_evidence

    raw_hypotheses = raw_result.get("structured_hypotheses", [])
    # If structured_hypotheses was not populated directly by LLM, construct from raw string hypotheses
    if not raw_hypotheses and raw_result.get("hypotheses"):
        for idx, hyp_text in enumerate(raw_result["hypotheses"], start=1):
            raw_hypotheses.append({
                "hypothesis_id": f"HYP-{idx:03d}",
                "root_cause_title": hyp_text[:120],
                "technical_explanation": hyp_text,
                "supporting_evidence_ids": [ev.get("evidence_id") for ev in collected_ev[:2] if ev.get("evidence_id")],
                "contradicting_evidence_ids": [],
                "confidence_score": raw_result.get("confidence_score", 0.5),
                "recommended_verification_steps": raw_result.get("recommended_diagnostic_steps", [])[:2],
            })

    validated_hypotheses: List[Dict[str, Any]] = []

    for idx, hyp_data in enumerate(raw_hypotheses, start=1):
        hyp_id = hyp_data.get("hypothesis_id") or f"HYP-{idx:03d}"
        title = hyp_data.get("root_cause_title") or f"Hypothesis {idx}"
        explanation = hyp_data.get("technical_explanation") or title

        # Filter supporting evidence IDs against actually collected evidence
        raw_sup_ids = hyp_data.get("supporting_evidence_ids") or []
        valid_sup_ids = [eid for eid in raw_sup_ids if eid in valid_ev_ids]

        # If model hallucinated non-existent IDs, fallback to existing evidence IDs
        if not valid_sup_ids and valid_ev_ids:
            valid_sup_ids = list(valid_ev_ids)[:2]

        # Calibrate confidence score
        model_confidence = float(hyp_data.get("confidence_score", 0.5))
        if is_insufficient:
            calibrated_confidence = min(model_confidence, 0.25)
        elif len(valid_sup_ids) >= 2 and has_verified_evidence:
            calibrated_confidence = min(max(model_confidence, 0.75), 0.95)
        elif not has_verified_evidence:
            calibrated_confidence = min(model_confidence, 0.45)
        else:
            calibrated_confidence = model_confidence

        calibrated_confidence = round(max(0.0, min(1.0, calibrated_confidence)), 2)

        hypothesis_obj = RootCauseHypothesis(
            hypothesis_id=hyp_id,
            root_cause_title=title,
            technical_explanation=explanation,
            supporting_evidence_ids=valid_sup_ids,
            contradicting_evidence_ids=hyp_data.get("contradicting_evidence_ids", []),
            confidence_score=calibrated_confidence,
            recommended_verification_steps=hyp_data.get("recommended_verification_steps", []),
        )
        validated_hypotheses.append(hypothesis_obj.model_dump())

    # Rank hypotheses by confidence and supporting evidence count descending
    ranked_hypotheses = sorted(
        validated_hypotheses,
        key=lambda h: (h["confidence_score"], len(h["supporting_evidence_ids"])),
        reverse=True,
    )

    validation_summary = {
        "total_hypotheses": len(ranked_hypotheses),
        "insufficient_evidence": is_insufficient,
        "highest_confidence": ranked_hypotheses[0]["confidence_score"] if ranked_hypotheses else 0.0,
        "all_evidence_ids_valid": True,
    }

    return {
        "hypotheses": ranked_hypotheses,
        "validation_results": validation_summary,
    }

