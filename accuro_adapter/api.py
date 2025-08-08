import os
from fastapi import FastAPI, HTTPException, Depends, Header, Query, Body
from typing import Optional, Union
from pydantic import BaseModel
from .client import find_appointment, cancel_appointment, fetch_patient_basic

class CancelRequest(BaseModel):
    tenant: str = "default"  
    patient_id: Union[str, int]
    date: str  # YYYY-MM-DD

RETELL_KEY = os.getenv("RETELL_WEBHOOK_KEY", "")

app = FastAPI(title="Accuro Adapter Service")

def verify_retell(authorization: str = Header(...)):
    """Simple bearer-token check for Retell webhook"""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != RETELL_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.post("/cancel", dependencies=[Depends(verify_retell)])
async def cancel(
    req: Optional[CancelRequest] = Body(None),
    patient_id: Optional[str] = Query(None, description="Patient ID if not provided in JSON body"),
    date: Optional[str] = Query(None, description="YYYY-MM-DD appointment date if not provided in body"),
    tenant: str = Query("default", description="Clinic tenant if not provided in body"),
):
    # Accept payload either from JSON body or from query parameters so testing tools can
    # easily pass constants without constructing JSON.
    if req is None:
        if not patient_id or not date:
            raise HTTPException(status_code=422, detail="patient_id and date are required")
        req = CancelRequest(tenant=tenant, patient_id=patient_id, date=date)
    appt = await find_appointment(str(req.patient_id), req.date)
    if not appt:
        raise HTTPException(status_code=404, detail="No appointment found")
    if appt.status == "cancelled":
        raise HTTPException(status_code=409, detail="Already cancelled")
    await cancel_appointment(appt.id)
    return {"message": "cancelled", "appointment_id": appt.id}

# ----------------------------- Read-only endpoints -----------------------------

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
