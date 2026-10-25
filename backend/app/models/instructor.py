import uuid
import enum
from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class DayOfWeek(str, enum.Enum):
    MON = "MON"
    TUE = "TUE"
    WED = "WED"
    THU = "THU"
    FRI = "FRI"
    SAT = "SAT"
    SUN = "SUN"


class InstructorAvailability(Base):
    __tablename__ = "instructor_availabilities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    instructor_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(String(10), nullable=False)
    time_slot_id = Column(String(36), ForeignKey("time_slots.id", ondelete="CASCADE"), nullable=False, index=True)
    is_available = Column(Boolean, default=False, nullable=False)  # False = unavailable
    reason = Column(String(255), nullable=True)

    instructor = relationship("User", back_populates="availabilities")
    time_slot = relationship("TimeSlot")
