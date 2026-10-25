from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_institution, require_role
from app.models.facility import Classroom
from app.models.user import User, UserRole
from app.schemas.facility import ClassroomCreate, ClassroomOut

router = APIRouter(prefix="/facilities", tags=["Facilities"])


@router.get("/classrooms", response_model=List[ClassroomOut])
def list_classrooms(
    building: Optional[str] = None,
    room_type: Optional[str] = None,
    inst_id: str = Depends(require_institution),
    db: Session = Depends(get_db)
):
    query = db.query(Classroom).filter(Classroom.institution_id == inst_id)
    if building:
        query = query.filter(Classroom.building == building)
    if room_type:
        query = query.filter(Classroom.room_type == room_type)
    return query.order_by(Classroom.building, Classroom.room_number).all()


@router.post("/classrooms", response_model=ClassroomOut, status_code=status.HTTP_201_CREATED)
def create_classroom(
    payload: ClassroomCreate,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    # Ensure physical rows * columns can accommodate designated capacity
    if (payload.rows * payload.columns) < payload.capacity:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Grid dimensions ({payload.rows}x{payload.columns}={payload.rows * payload.columns}) cannot be smaller than room capacity ({payload.capacity})"
        )

    classroom = Classroom(
        institution_id=inst_id,
        name=payload.name,
        building=payload.building,
        room_number=payload.room_number,
        capacity=payload.capacity,
        room_type=payload.room_type,
        rows=payload.rows,
        columns=payload.columns
    )
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return classroom


@router.delete("/classrooms/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classroom(
    classroom_id: str,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    classroom = db.query(Classroom).filter(
        Classroom.id == classroom_id,
        Classroom.institution_id == inst_id
    ).first()
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")

    db.delete(classroom)
    db.commit()
    return None
