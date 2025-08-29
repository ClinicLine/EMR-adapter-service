from pydantic import BaseModel

class PatientBasic(BaseModel):
    id: str
    given_name: str
    family_name: str
    date_of_birth: str
    health_card: str

class AppointmentBasic(BaseModel):
    id: str
    patient_id: str | None = None
    start: str | None = None  # ISO-8601 dateTime
    end: str | None = None
    status: str | None = None

class AvailabilitySlot(BaseModel):
    """Represents a free slot offered to the caller."""
    start: str  # ISO-8601 dateTime
    end: str

class BookRequest(BaseModel):
    patient_id: str
    start: str  # desired start datetime ISO

class BookResponse(BaseModel):
    confirmation_code: str
    appointment_time: str  # ISO

class RescheduleRequest(BaseModel):
    appointment_id: str | None = None
    patient_id: str | None = None
    old_time: str
    new_start: str

class RescheduleResponse(BaseModel):
    new_time: str
  