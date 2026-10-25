from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role, require_institution
from app.models.institution import Institution
from app.models.user import User, UserRole
from app.schemas.institution import InstitutionOut, InstitutionUpdate

router = APIRouter(prefix="/institutions", tags=["Institutions"])


@router.get("/current", response_model=InstitutionOut)
def get_current_institution(
    inst_id: str = Depends(require_institution),
    db: Session = Depends(get_db)
):
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")
    return inst


@router.patch("/current", response_model=InstitutionOut)
def update_current_institution(
    payload: InstitutionUpdate,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")
    
    if payload.name is not None:
        inst.name = payload.name
    if payload.domain is not None:
        inst.domain = payload.domain

    db.commit()
    db.refresh(inst)
    return inst
