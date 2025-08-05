"""Async Accuro API client focused on Patient lookup.
Assumes OAuth2 client-credentials flow.
"""
from __future__ import annotations
import os
import time
import httpx
from dotenv import load_dotenv
from .models import PatientBasic, AppointmentBasic

load_dotenv()

_BASE_URL = os.getenv("ACCURO_BASE_URL", "https://sandbox.accuroemr.com/api")
_TOKEN_URL = os.getenv("ACCURO_TOKEN_URL", f"{_BASE_URL}/oauth2/token")
_CLIENT_ID = os.getenv("ACCURO_CLIENT_ID")
_CLIENT_SECRET = os.getenv("ACCURO_CLIENT_SECRET")

_TOKEN_CACHE: dict[str, float | str] = {"token": None, "exp": 0.0}

async def _get_token() -> str:
    """Fetch and cache bearer token for ~55 minutes."""
    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["exp"]:
        return _TOKEN_CACHE["token"]  # type: ignore

    async with httpx.AsyncClient(http2=True, timeout=15) as client:
        resp = await client.post(
            _TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(_CLIENT_ID, _CLIENT_SECRET),
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
        # default expires_in 3600 seconds = 1 hour
        _TOKEN_CACHE.update(token=token, exp=now + data.get("expires_in", 3600) - 300)
        return token

async def fetch_patient_basic(patient_id: str) -> PatientBasic:
    """Return basic demographic for a patient ID."""
    headers = {"Authorization": f"Bearer {await _get_token()}", "Accept": "application/json"}
    async with httpx.AsyncClient(http2=True, timeout=15) as client:
        resp = await client.get(f"{_BASE_URL}/Patient/{patient_id}", headers=headers)
        resp.raise_for_status()
        payload = resp.json()

    name_block = payload.get("name", [{}])[0]
    identifier_block = payload.get("identifier", [{}])[0]

    return PatientBasic(
        id=payload.get("id", patient_id),
        given_name=name_block.get("given", [""])[0],
        family_name=name_block.get("family", ""),
        date_of_birth=payload.get("birthDate", ""),
        health_card=identifier_block.get("value", ""),
    )

async def fetch_appointment(appt_id: str) -> AppointmentBasic:
    """Fetch appointment details by ID."""
    headers = {"Authorization": f"Bearer {await _get_token()}", "Accept": "application/json"}
    async with httpx.AsyncClient(http2=True, timeout=15) as client:
        resp = await client.get(f"{_BASE_URL}/Appointment/{appt_id}", headers=headers)
        resp.raise_for_status()
        payload = resp.json()

    return AppointmentBasic(
        id=payload.get("id", appt_id),
        patient_id=payload.get("subject", {}).get("reference", "").replace("Patient/", ""),
        start=payload.get("start"),
        end=payload.get("end"),
        status=payload.get("status"),
    )

async def cancel_appointment(appt_id: str) -> None:
    """Mark an appointment as cancelled. Accuro sandbox may require PATCH operation."""
    headers = {"Authorization": f"Bearer {await _get_token()}", "Content-Type": "application/json-patch+json"}
    patch_body = [{"op": "replace", "path": "/status", "value": "cancelled"}]
    async with httpx.AsyncClient(http2=True, timeout=15) as client:
        resp = await client.patch(f"{_BASE_URL}/Appointment/{appt_id}", headers=headers, json=patch_body)
        resp.raise_for_status()

async def find_appointment(patient_id: str, date_iso: str) -> AppointmentBasic | None:
    """Return the first appointment for a patient on a given date (YYYY-MM-DD) or None."""
    headers = {"Authorization": f"Bearer {await _get_token()}", "Accept": "application/json"}
    params = {"patient": patient_id, "date": date_iso}
    async with httpx.AsyncClient(http2=True, timeout=15) as client:
        resp = await client.get(f"{_BASE_URL}/Appointment", headers=headers, params=params)
        resp.raise_for_status()
        bundle = resp.json()

    entries = bundle.get("entry", [])
    if not entries:
        return None

    resource = entries[0]["resource"]
    return AppointmentBasic(
        id=resource.get("id"),
        patient_id=patient_id,
        start=resource.get("start"),
        end=resource.get("end"),
        status=resource.get("status"),
    )
