from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_institution, require_role
from app.models.academic import AcademicTerm, Department, ProgramBatch
from app.models.user import User, UserRole
from app.schemas.academic import (
    AcademicTermCreate,
    AcademicTermOut,
    DepartmentCreate,
    DepartmentOut,
    ProgramBatchCreate,
    ProgramBatchOut,
)

router = APIRouter(prefix="/academic", tags=["Academic"])


# --- Terms ---
@router.get("/terms", response_model=List[AcademicTermOut])
def list_terms(inst_id: str = Depends(require_institution), db: Session = Depends(get_db)):
    return db.query(AcademicTerm).filter(AcademicTerm.institution_id == inst_id).all()


@router.post("/terms", response_model=AcademicTermOut, status_code=status.HTTP_201_CREATED)
def create_term(
    payload: AcademicTermCreate,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    if payload.start_date >= payload.end_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="End date must be after start date")

    term = AcademicTerm(
        institution_id=inst_id,
        name=payload.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_active=payload.is_active
    )
    db.add(term)
    db.commit()
    db.refresh(term)
    return term


# --- Departments ---
@router.get("/departments", response_model=List[DepartmentOut])
def list_departments(inst_id: str = Depends(require_institution), db: Session = Depends(get_db)):
    return db.query(Department).filter(Department.institution_id == inst_id).all()


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    dept = Department(
        institution_id=inst_id,
        name=payload.name,
        code=payload.code.upper()
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


# --- Batches ---
@router.get("/batches", response_model=List[ProgramBatchOut])
def list_batches(inst_id: str = Depends(require_institution), db: Session = Depends(get_db)):
    return db.query(ProgramBatch).filter(ProgramBatch.institution_id == inst_id).all()


@router.post("/batches", response_model=ProgramBatchOut, status_code=status.HTTP_201_CREATED)
def create_batch(
    payload: ProgramBatchCreate,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    dept = db.query(Department).filter(
        Department.id == payload.department_id,
        Department.institution_id == inst_id
    ).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    batch = ProgramBatch(
        institution_id=inst_id,
        department_id=payload.department_id,
        name=payload.name,
        student_count=payload.student_count,
        semester_level=payload.semester_level
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch
