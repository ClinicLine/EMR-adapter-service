import json, pathlib
import pytest, respx, httpx
from accuro_adapter.models import AppointmentBasic
from accuro_adapter import client as cl


# inject dummy credentials so httpx.BasicAuth doesn't choke during mocked calls
cl._CLIENT_ID = "dummy"
cl._CLIENT_SECRET = "dummy"

FIX = pathlib.Path(__file__).parent / "fixtures"
TOKEN_RESP = {"access_token": "fake", "expires_in": 3600}
BASE = "https://sandbox.accuroemr.com"

@pytest.mark.asyncio
async def test_find_appointment():
    bundle = json.loads((FIX / "appointment_get.json").read_text())
    with respx.mock(base_url=BASE) as m:
        m.post("/api/oauth2/token").respond(200, json=TOKEN_RESP)
        m.get("/api/Appointment").respond(200, json=bundle)

        appt = await cl.find_appointment("99", "2025-08-15")
        assert isinstance(appt, AppointmentBasic)
        assert appt.id == "appt-123"
        assert appt.status == "booked"

@pytest.mark.asyncio
async def test_cancel_appointment():
    with respx.mock(base_url=BASE) as m:
        m.post("/api/oauth2/token").respond(200, json=TOKEN_RESP)
        m.patch("/api/Appointment/appt-123").respond(200, json={"status": "cancelled"})

        # reset token cache so POST /token is invoked in this test
        cl._TOKEN_CACHE.update(token=None, exp=0)

        await cl.cancel_appointment("appt-123")
        # ensure a PATCH call was made
        assert any(call.request.method == "PATCH" for call in m.calls)
