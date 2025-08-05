import os
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from .client import find_appointment, cancel_appointment

class CancelRequest(BaseModel):
    tenant: str = "default"  
    patient_id: str
    date: str  # YYYY-MM-DD

RETELL_KEY = os.getenv("RETELL_WEBHOOK_KEY", "")

app = FastAPI(title="Accuro Adapter Service")

def verify_retell(authorization: str = Header(...)):
    """Simple bearer-token check for Retell webhook"""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != RETELL_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.post("/cancel", dependencies=[Depends(verify_retell)])
async def cancel(req: CancelRequest):
    appt = await find_appointment(req.patient_id, req.date)
    if not appt:
        raise HTTPException(status_code=404, detail="No appointment found")
    if appt.status == "cancelled":
        raise HTTPException(status_code=409, detail="Already cancelled")
    await cancel_appointment(appt.id)
    return {"message": "cancelled", "appointment_id": appt.id}
