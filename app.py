import os
import datetime as dt
import dateparser
from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from square.client import Client

# --- Env (set these in Render later) ---
SQUARE_ENV = os.getenv("SQUARE_ENV", "sandbox")
SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN", "")
SQUARE_LOCATION_ID = os.getenv("SQUARE_LOCATION_ID", "")
SQUARE_TEAM_MEMBER_ID = os.getenv("SQUARE_TEAM_MEMBER_ID", "")
SQUARE_SERVICE_VARIATION_ID = os.getenv("SQUARE_SERVICE_VARIATION_ID", "")

app = FastAPI(title="NOVA Cuts AI Manager (SMS MVP)")

def sq():
    return Client(environment=SQUARE_ENV, access_token=SQUARE_ACCESS_TOKEN)

def ensure_customer(client, name: str, phone: str):
    body = {"given_name": name, "phone_number": phone}
    resp = client.customers.create_customer(body)
    if resp.is_success():
        return resp.body["customer"]["id"]
    return None

def search_availability(client, location_id, team_member_id, service_variation_id, start_at, end_at):
    body = {
        "query": {
            "filter": {
                "location_id": location_id,
                "segment_filters": [{
                    "service_variation_id": service_variation_id,
                    "team_member_id_filter": {"any": [team_member_id]}
                }],
                "start_at_range": {"start_at": start_at, "end_at": end_at}
            }
        }
    }
    return client.bookings.search_availability(body)

def create_booking(client, location_id, customer_id, start_at, team_member_id, service_variation_id, service_version=None):
    segment = {
        "team_member_id": team_member_id,
        "service_variation_id": service_variation_id
    }
    if service_version:
        segment["service_variation_version"] = service_version
    body = {
        "booking": {
            "location_id": location_id,
            "customer_id": customer_id,
            "start_at": start_at,
            "appointment_segments": [segment]
        },
        "idempotency_key": start_at.replace(':','-').replace('+','_')
    }
    return client.bookings.create_booking(body)

@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"

@app.post("/sms")
async def sms(From: str = Form(...), Body: str = Form(...)):
    text = Body.strip().lower()
    resp = MessagingResponse()

    # parse name
    name = "Guest"
    if " for " in text:
        name = text.split(" for ", 1)[1].strip().title() or "Guest"

    # parse time
    when = dateparser.parse(text, settings={'PREFER_DATES_FROM': 'future'})
    if not when:
        resp.message("I couldn’t read the date/time. Try: 'Book haircut Friday 3pm for Kwan'.")
        return PlainTextResponse(str(resp), media_type="application/xml")

    start_at = when.replace(second=0, microsecond=0)
    end_at = start_at + dt.timedelta(hours=3)

    try:
        client = sq()

        # 1) ensure/create customer
        cust_id = ensure_customer(client, name, From)
        if not cust_id:
            c = client.customers.create_customer({"given_name": name})
            cust_id = c.body["customer"]["id"]

        # 2) search availability
        iso_start = start_at.isoformat()
        iso_end = end_at.isoformat()
        avail = search_availability(client,
                                    SQUARE_LOCATION_ID,
                                    SQUARE_TEAM_MEMBER_ID,
                                    SQUARE_SERVICE_VARIATION_ID,
                                    iso_start, iso_end)

        if not avail.is_success():
            msg = avail.errors[0]["detail"] if getattr(avail, "errors", None) else "availability error"
            resp.message(f"Sorry, I couldn’t check availability ({msg}).")
            return PlainTextResponse(str(resp), media_type="application/xml")

        slots = avail.body.get("availabilities", [])
        if not slots:
            resp.message("No open slots in that window. Want me to try a different time?")
            return PlainTextResponse(str(resp), media_type="application/xml")

        chosen = slots[0]
        slot_start = chosen["start_at"]

        # 3) create booking
        booking = create_booking(client,
                                 SQUARE_LOCATION_ID,
                                 cust_id,
                                 slot_start,
                                 SQUARE_TEAM_MEMBER_ID,
                                 SQUARE_SERVICE_VARIATION_ID)
        if not booking.is_success():
            msg = booking.errors[0]["detail"] if getattr(booking, "errors", None) else "booking error"
            resp.message(f"Couldn’t book that slot ({msg}). Try another time?")
            return PlainTextResponse(str(resp), media_type="application/xml")

        human_time = slot_start.replace('T',' ').replace('Z',' UTC')
        resp.message(f"You're booked for a haircut on {human_time}. Reply with a new time to change it.")
        return PlainTextResponse(str(resp), media_type="application/xml")

    except Exception as e:
        resp.message(f"Sorry, I hit a snag: {e}")
        return PlainTextResponse(str(resp), media_type="application/xml")
