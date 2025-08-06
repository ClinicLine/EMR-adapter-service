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
  