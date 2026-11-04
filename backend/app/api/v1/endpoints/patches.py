import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.repositories import CodePatchRepository
from app.schemas.code_patch import CodePatchResponse
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

