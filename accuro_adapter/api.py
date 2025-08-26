import os
from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from .models import AvailabilitySlot, BookRequest, BookResponse, RescheduleRequest, RescheduleResponse
from .client import find_appointment, cancel_appointment, fetch_patient_basic

class SearchResp(BaseModel):
    patient_id: str

class CancelRequest(BaseModel):
    tenant: str = "default"  
    patient_id: Union[str, int]
    date: str = Field(alias="appt_date")  

    model_config = {
        "populate_by_name": True  
    }

RETELL_KEY = os.getenv("RETELL_WEBHOOK_KEY", "")
# HTTPBearer scheme so Swagger-UI can attach the Authorization header globally
auth_scheme = HTTPBearer(auto_error=False)

app = FastAPI(title="Accuro Adapter Service")

def verify_retell(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    """Validate Bearer token provided via Authorization header"""
    if credentials is None or credentials.scheme.lower() != "bearer" or credentials.credentials != RETELL_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.post("/cancel", dependencies=[Depends(verify_retell)])
async def cancel(
    req: Optional[CancelRequest] = Body(None),
    patient_id: Optional[str] = Query(None, description="Patient ID if not provided in JSON body"),
    appt_date: Optional[str] = Query(None, alias="appt_date", description="YYYY-MM-DD appointment date if not provided in body"),
    tenant: str = Query("default", description="Clinic tenant if not provided in body"),
):
    # Accept payload either from JSON body or from query parameters so testing tools can
    # pass constants without constructing JSON.
    if req is None:
        if not patient_id or not appt_date:
            raise HTTPException(status_code=422, detail="patient_id and appt_date are required")
        appt_date_q = appt_date
        req = CancelRequest(tenant=tenant, patient_id=patient_id, date=appt_date_q)
    # Short-circuit in OFFLINE_MODE – always succeed
    if os.getenv("OFFLINE_MODE", "0") == "1":
        return {"message": "cancelled", "appointment_id": "offline-demo"}

    appt = await find_appointment(str(req.patient_id), req.date)
    if not appt:
        raise HTTPException(status_code=404, detail="No appointment found")
    if appt.status == "cancelled":
        raise HTTPException(status_code=409, detail="Already cancelled")
    await cancel_appointment(appt.id)
    return {"message": "cancelled", "appointment_id": appt.id}

# Search patient endpoint

@app.get("/patient/search", dependencies=[Depends(verify_retell)])
async def patient_search(
    first_name: Optional[str] = Query(None, alias="first_name"),
    last_name: Optional[str] = Query(None, alias="last_name"),
    dob: str = Query(...),
):
    """Return stub patient_id while OFFLINE."""
    first_name = first_name or "John"
    last_name = last_name or "Doe"

    if os.getenv("OFFLINE_MODE", "0") == "1":
        # Ignore names; always return demo ID
        return SearchResp(patient_id="123")

    raise HTTPException(status_code=501, detail="Search not implemented in live mode yet")

# Booking related endpoints -------------------------------------------------

@app.get("/availability", dependencies=[Depends(verify_retell)], response_model=list[AvailabilitySlot])
async def list_availability(patient_id: str = Query(...)):
    """Return up to three open slots for the patient. In OFFLINE_MODE generate demo data."""
    if os.getenv("OFFLINE_MODE", "0") == "1":
        base = datetime.utcnow().replace(hour=13, minute=0, second=0, microsecond=0)
        return [
            AvailabilitySlot(start=(base + timedelta(days=1)).isoformat(), end=(base + timedelta(days=1, minutes=15)).isoformat()),
            AvailabilitySlot(start=(base + timedelta(days=4)).isoformat(), end=(base + timedelta(days=4, minutes=15)).isoformat()),
            AvailabilitySlot(start=(base + timedelta(days=7)).isoformat(), end=(base + timedelta(days=7, minutes=15)).isoformat()),
        ]
    raise HTTPException(status_code=501, detail="Live availability not implemented")

@app.post("/book", dependencies=[Depends(verify_retell)], response_model=BookResponse)
async def book_appt(req: BookRequest):
    """Book an appointment (stub)."""
    if os.getenv("OFFLINE_MODE", "0") == "1":
        return BookResponse(confirmation_code="demo-12345", appointment_time=req.start)
    raise HTTPException(status_code=501, detail="Live booking not implemented")

@app.post("/reschedule", dependencies=[Depends(verify_retell)], response_model=RescheduleResponse)
async def reschedule_appt(req: RescheduleRequest):
    """Reschedule an appointment (stub)."""
    if os.getenv("OFFLINE_MODE", "0") == "1":
        return RescheduleResponse(new_time=req.new_start)
    raise HTTPException(status_code=501, detail="Live reschedule not implemented")

@app.post("/handoff", dependencies=[Depends(verify_retell)], status_code=204)
async def handoff():
    """Notify backend of human handoff. In offline mode we just ACK."""
    return None

# Read-only endpoints 

@app.get("/patient/{patient_id}", dependencies=[Depends(verify_retell)])
async def get_patient(patient_id: str):
    """Return basic demographic info for a patient."""
    patient = await fetch_patient_basic(str(patient_id))
    return patient.model_dump()

@app.get("/appointment", dependencies=[Depends(verify_retell)])
async def get_appointment(
    patient_id: str = Query(..., description="Patient ID"),
    date: str = Query(..., description="YYYY-MM-DD appointment start date"),
):
    """Return appointment details for a patient on a given date (if any)."""
    appt = await find_appointment(str(patient_id), date)
    if not appt:
        raise HTTPException(status_code=404, detail="No appointment found")
    return appt.model_dump()
