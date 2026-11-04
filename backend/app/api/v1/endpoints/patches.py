import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.application import (
    ApprovalIntegrityError,
    ApprovalService,
    AuthenticationRequiredError,
    GitExecutionError,
    GitWorktreeError,
    InvalidBaseCommitError,
    PatchAlreadyAppliedError,
    PatchAlreadyApprovedError,
    PatchAlreadyRejectedError,
    PatchApplicationError,
    PatchApplicationService,
    PatchConcurrentModificationError,
    PatchIntegrityError,
    PatchNotApprovedError,
    PatchNotFoundError,
    SecurityViolationError,
)
from app.db.dependencies import get_db
from app.repositories import CodePatchRepository
from app.schemas.approval import ApprovalResponse, PatchApproveRequest, PatchRejectRequest
from app.schemas.code_patch import CodePatchResponse, PatchApplicationStatusResponse
from app.schemas.common import BaseResponse

router = APIRouter()


@router.get(
    "/patches/{patch_id}",
    response_model=BaseResponse[CodePatchResponse],
    summary="Get Code Patch Detail",
    description="Retrieve a single code patch by unique ID, including diff content and SHA-256 hash.",
)
def get_code_patch(
    patch_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BaseResponse[CodePatchResponse]:
    """Retrieve code patch record by UUID."""
    patch = CodePatchRepository.get_by_id(db, patch_id)
    if patch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Code patch with ID '{patch_id}' not found",
        )

    resp = CodePatchResponse.model_validate(patch)
    resp.is_hash_valid = CodePatchRepository.verify_patch_hash(patch)

    return BaseResponse(
        success=True,
        message="Code patch retrieved successfully",
        data=resp,
    )


@router.post(
    "/patches/{patch_id}/approve",
    response_model=BaseResponse[ApprovalResponse],
    summary="Approve Code Patch",
    description="Approve a proposed code patch after verifying its cryptographic SHA-256 integrity.",
)
def approve_code_patch(
    patch_id: uuid.UUID,
    request: Optional[PatchApproveRequest] = None,
    db: Session = Depends(get_db),
) -> BaseResponse[ApprovalResponse]:
    """Approve a pending code patch."""
    comment = request.comment if request else None
    try:
        approval = ApprovalService.approve_patch(
            db=db,
            patch_id=patch_id,
            comment=comment,
        )
        return BaseResponse(
            success=True,
            message="Code patch successfully approved",
            data=approval,
        )
    except PatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (
        PatchAlreadyApprovedError,
        PatchAlreadyRejectedError,
        PatchAlreadyAppliedError,
        PatchNotApprovedError,
        PatchConcurrentModificationError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except (PatchIntegrityError, ApprovalIntegrityError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except AuthenticationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/patches/{patch_id}/reject",
    response_model=BaseResponse[ApprovalResponse],
    summary="Reject Code Patch",
    description="Reject a proposed code patch with an optional reviewer reason.",
)
def reject_code_patch(
    patch_id: uuid.UUID,
    request: Optional[PatchRejectRequest] = None,
    db: Session = Depends(get_db),
) -> BaseResponse[ApprovalResponse]:
    """Reject a pending code patch."""
    reason = request.reason if request else None
    try:
        rejection = ApprovalService.reject_patch(
            db=db,
            patch_id=patch_id,
            reason=reason,
        )
        return BaseResponse(
            success=True,
            message="Code patch successfully rejected",
            data=rejection,
        )
    except PatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (
        PatchAlreadyApprovedError,
        PatchAlreadyRejectedError,
        PatchAlreadyAppliedError,
        PatchNotApprovedError,
        PatchConcurrentModificationError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except (PatchIntegrityError, ApprovalIntegrityError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except AuthenticationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/patches/{patch_id}/approval",
    response_model=BaseResponse[Optional[ApprovalResponse]],
    summary="Get Patch Approval Status",
    description="Retrieve the latest approval decision for a code patch.",
)
def get_patch_approval(
    patch_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BaseResponse[Optional[ApprovalResponse]]:
    """Retrieve current approval record."""
    patch = CodePatchRepository.get_by_id(db, patch_id)
    if patch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Code patch with ID '{patch_id}' not found",
        )

    approval = ApprovalService.get_latest_approval(db, patch_id)
    return BaseResponse(
        success=True,
        message="Approval record retrieved successfully",
        data=approval,
    )


@router.get(
    "/patches/{patch_id}/approval/history",
    response_model=BaseResponse[List[ApprovalResponse]],
    summary="Get Patch Approval History",
    description="Retrieve the complete chronological approval history for a code patch.",
)
def get_patch_approval_history(
    patch_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BaseResponse[List[ApprovalResponse]]:
    """Retrieve all approval decisions for this patch."""
    try:
        history = ApprovalService.get_approval_history(db, patch_id)
        return BaseResponse(
            success=True,
            message=f"Retrieved {len(history)} approval records",
            data=history,
        )
    except PatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/patches/{patch_id}/apply",
    response_model=BaseResponse[PatchApplicationStatusResponse],
    summary="Apply Approved Code Patch",
    description="Apply an approved code patch inside an isolated Git worktree after cryptographic verification.",
)
def apply_code_patch(
    patch_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BaseResponse[PatchApplicationStatusResponse]:
    """Execute controlled patch application."""
    try:
        result = PatchApplicationService.apply_patch(db=db, patch_id=patch_id)
        return BaseResponse(
            success=True,
            message="Patch successfully applied inside isolated worktree",
            data=result,
        )
    except PatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (
        PatchNotApprovedError,
        PatchAlreadyAppliedError,
        PatchAlreadyRejectedError,
        PatchConcurrentModificationError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except (PatchIntegrityError, ApprovalIntegrityError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SecurityViolationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except (InvalidBaseCommitError, GitWorktreeError, GitExecutionError, PatchApplicationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/patches/{patch_id}/application",
    response_model=BaseResponse[PatchApplicationStatusResponse],
    summary="Get Patch Application Status",
    description="Retrieve execution details, modified files, and application state of a code patch.",
)
def get_patch_application_status(
    patch_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> BaseResponse[PatchApplicationStatusResponse]:
    """Retrieve patch application status."""
    try:
        result = PatchApplicationService.get_application_status(db=db, patch_id=patch_id)
        return BaseResponse(
            success=True,
            message="Patch application status retrieved successfully",
            data=result,
        )
    except PatchNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
