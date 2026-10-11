from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
import requests
import os
import re
import pathlib

# =============== ENV VARIABLES ================
BASE_DIR = pathlib.Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
print("WHATSAPP_TOKEN loaded:", "YES" if os.getenv("WHATSAPP_TOKEN") else "NO")
print("PHONE_NUMBER_ID loaded:", os.getenv("PHONE_NUMBER_ID"))

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
DEFAULT_WHATSAPP_RECIPIENT = (
    os.getenv("WHATSAPP_TEST_NUMBER")
    or os.getenv("PERSONAL_WHATSAPP_NUMBER")
    or ""
).strip()

# ================= SERVICE URLS =================

HOME_SERVICE_URL        = os.getenv("HOME_SERVICE_URL",        "http://127.0.0.1:5001")
CHATBOT_SERVICE_URL     = os.getenv("CHATBOT_SERVICE_URL",     "http://127.0.0.1:7600")
ASSET_SERVICE_URL       = os.getenv("ASSET_SERVICE_URL",       "http://127.0.0.1:8090")
INTERNSHIP_SERVICE_URL  = os.getenv("INTERNSHIP_SERVICE_URL",  "http://127.0.0.1:5050")
MS365_SERVICE_URL       = os.getenv("MS365_SERVICE_URL",       "http://127.0.0.1:7700")
EMPLOYEE_SERVICE_URL    = os.getenv("EMPLOYEE_SERVICE_URL",    "http://127.0.0.1:8002")
BLOGGER_SERVICE_URL     = os.getenv("BLOGGER_SERVICE_URL",     "http://127.0.0.1:7500")
REDIS_SERVICE_URL       = os.getenv("REDIS_SERVICE_URL",       "http://127.0.0.1:6390")
BRS_SERVICE_URL         = os.getenv("BRS_SERVICE_URL",         "http://127.0.0.1:8020")
BILLING_SERVICE_URL     = os.getenv("BILLING_SERVICE_URL",     "http://127.0.0.1:8010")
RAG_SERVICE_URL         = os.getenv("RAG_SERVICE_URL",         "http://127.0.0.1:8050")
STUDENT_SERVICE_URL     = os.getenv("STUDENT_SERVICE_URL",     "http://127.0.0.1:8030")
MEETING_SERVICE_URL = os.getenv("MEETING_SERVICE_URL", "http://127.0.0.1:9000")


LAMBDA_URL = 'https://lwug4xhfz27whiuu3acjfwsgtm0ttwja.lambda-url.eu-north-1.on.aws/'
STATIC_CDN = "https://d1pjjckqswt5z7.cloudfront.net"

CANONICAL_HOST = os.getenv("CANONICAL_HOST","www.chakorahub.com").strip().lower()
INTERNSHIP_PUBLIC_HOST = os.getenv("INTERNSHIP_PUBLIC_HOST","api.chakorahub.com").strip().lower()

app = FastAPI(title="ChakoraHub WhatsApp Notification Service")


def _normalize_phone_number(phone_number: str) -> str:
    cleaned = re.sub(r"\D", "", phone_number or "")
    if cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]
    if cleaned.startswith("91") and len(cleaned) == 12:
        return cleaned
    if len(cleaned) == 10:
        return f"91{cleaned}"
    return cleaned


def _send_whatsapp_text_message(phone_number: str, message_text: str):

    recipient = _normalize_phone_number(phone_number)

    print(f"Recipient: {recipient}")
    print(f"WHATSAPP_TOKEN loaded: {'YES' if WHATSAPP_TOKEN else 'NO'}")
    print(f"PHONE_NUMBER_ID: {PHONE_NUMBER_ID}")

    if not recipient:
        raise HTTPException(status_code=400, detail="Recipient phone number is required")

    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        raise HTTPException(status_code=500, detail="WhatsApp credentials are not configured")

    whatsapp_url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
    "messaging_product": "whatsapp",
    "to": recipient,
    "type": "text",
    "text": {
        "preview_url": False,
        "body": message_text,
        },
    }

    print("Payload:", payload)

    whatsapp_response = requests.post(
        whatsapp_url,
        headers=headers,
        json=payload,
        timeout=30,
    )

    print("Meta Status:", whatsapp_response.status_code)
    print("Meta Response:", whatsapp_response.text)

    try:
        whatsapp_json = whatsapp_response.json()
    except ValueError:
        whatsapp_json = {"raw_response": whatsapp_response.text}

    if whatsapp_response.status_code != 200:
        raise HTTPException(status_code=500, detail=whatsapp_json)

    return whatsapp_json

# =========================================================
# HEALTH CHECK
# =========================================================
@app.get("/health")
def health():
    return {
        "status": "success",
        "service": "whatsapp-notification-service"
    }


print(f"TOKEN FROM PYTHON => {WHATSAPP_TOKEN}")
print(f"PHONE_NUMBER_ID => {PHONE_NUMBER_ID}")
# =========================================================
# SEND SESSION REMINDER
# =========================================================
@app.post("/send-session-reminder/{student_id}/{meeting_id}")
def send_session_reminder(student_id: int, meeting_id: int):
    try:
        # =================================================
        # STEP 1 - FETCH STUDENT DETAILS
        # =================================================
        student_response = requests.get(
            f"{STUDENT_SERVICE_URL}/api/student/profile/{student_id}"
        )

        if student_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Unable to fetch student details"
            )

        student_data = student_response.json()
        student_name = student_data.get("student_name")
        phone_number = student_data.get("phone_number")

        # =================================================
        # STEP 2 - FETCH MEETING DETAILS
        # =================================================
        meeting_response = requests.get(
            f"{MEETING_SERVICE_URL}/api/meeting/{meeting_id}"
        )

        if meeting_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Unable to fetch meeting details"
            )

        meeting_data = meeting_response.json()
        course_id = meeting_data.get("course_id")
        trainer_name = meeting_data.get("trainer_name")
        session_time = meeting_data.get("session_time")
        meeting_link = meeting_data.get("meeting_link")

        # =================================================
        # STEP 3 - FETCH COURSE DETAILS
        # =================================================
        course_response = requests.get(
            f"{HOME_SERVICE_URL}/home/courses/{course_id}"
        )

        if course_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Unable to fetch course details"
            )
        course_data = course_response.json()
        course_name = course_data.get("course_name")

        # =================================================
        # STEP 4 - SEND WHATSAPP TEMPLATE
        # =================================================
        whatsapp_url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": _normalize_phone_number(phone_number),
            "type": "template",
            "template": {
                "name": "session_reminder",
                "language": {
                    "code": "en"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": student_name},   # {{1}} Hello
                            {"type": "text", "text": course_name},    # {{2}} Topic
                            {"type": "text", "text": "ChakoraHub"},   # {{3}} Trainer
                            {"type": "text", "text": "Now"},          # {{4}} Time
                            {"type": "text", "text": "chakorahub.com"} # {{5}} Link
    ]
                    }
                ]
            }
        }

        whatsapp_response = requests.post(
            whatsapp_url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        whatsapp_json = whatsapp_response.json()

        if whatsapp_response.status_code not in (200, 201):
            raise HTTPException(
                status_code=500,
                detail=whatsapp_json
            )

        return {
            "status": "success",
            "student": student_name,
            "course": course_name,
            "meta_response": whatsapp_json
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/send-registration-message")
def send_registration_message(payload: dict):
    phone_number = str(payload.get("phone_number") or DEFAULT_WHATSAPP_RECIPIENT).strip()
    student_name = str(payload.get("student_name") or "Student").strip()
    student_id   = str(payload.get("student_id")   or "").strip()
    course_name  = str(payload.get("course_name")  or "your course").strip()

    if not phone_number:
        raise HTTPException(status_code=400, detail="phone_number is required")

    recipient = _normalize_phone_number(phone_number)

    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        raise HTTPException(status_code=500, detail="WhatsApp credentials not configured")

    whatsapp_url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    # ── Template message (required for system-initiated conversations) ──
    template_payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": {
            "name": "session_reminder",   # ← your approved template name
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": "Subhash"},
                        {"type": "text", "text": "TEST001"},
                        {"type": "text", "text": "AWS TEST"},
                        {"type": "text", "text": "Now"},          # {{4}} Time
                        {"type": "text", "text": "chakorahub.com"}, # {{5}} Link
                    ]
                }
            ]
        }
    }

    print("Template payload:", template_payload)
    resp = requests.post(whatsapp_url, headers=headers, json=template_payload, timeout=30)
    print("Meta Status:", resp.status_code)
    print("Meta Response:", resp.text)

    try:
        resp_json = resp.json()
    except ValueError:
        resp_json = {"raw": resp.text}

    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=resp_json)

    return {
        "status": "success",
        "phone_number": recipient,
        "meta_response": resp_json,
    }


@app.post("/send-class-update")
def send_class_update(payload: dict):
    """
    Sends WhatsApp notification for upcoming class session.
    Payload:
        phone_number: str
        student_name: str (default 'Student')
        trainer_name: str (default 'ChakoraHub Trainer')
        course_name: str (e.g. session title)
        session_time: str (e.g. '10:00 AM - 11:30 AM IST, 26 Aug 2026')
        agenda: str (captured from Teams)
        meeting_link: str (Teams meeting link)
        send_as_text: bool (optional, fallback or direct text message)
    """
    phone_number = str(payload.get("phone_number") or DEFAULT_WHATSAPP_RECIPIENT).strip()
    student_name = str(payload.get("student_name") or "Student").strip()
    trainer_name = str(payload.get("trainer_name") or "ChakoraHub Trainer").strip()
    course_name  = str(payload.get("course_name")  or "Upcoming Class Session").strip()
    session_time = str(payload.get("session_time") or "Upcoming").strip()
    agenda       = str(payload.get("agenda")       or "Please join on time.").strip()
    meeting_link = str(payload.get("meeting_link") or "https://chakorahub.com").strip()
    send_as_text = bool(payload.get("send_as_text", False))

    force_override = os.getenv("FORCE_TEST_RECIPIENT_ONLY", "").strip()
    if force_override:
        print(f"🔒 [WABA SAFETY LOCK] Overriding recipient to test phone: {force_override} (NRM_USERS protected)")
        phone_number = force_override

    recipient = _normalize_phone_number(phone_number)

    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        raise HTTPException(status_code=500, detail="WhatsApp credentials not configured")

    whatsapp_url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    # If sending as plain text or fallback:
    if send_as_text:
        formatted_body = (
            f"📢 *Upcoming Class Update*\n\n"
            f"Hello {student_name},\n\n"
            f"👤 *Trainer:* {trainer_name}\n"
            f"📚 *Session on:* {course_name}\n"
            f"⏰ *Timings:* {session_time}\n"
            f"📝 *Agenda:*\n{agenda}\n\n"
            f"🔗 *Join Teams Meeting:*\n{meeting_link}"
        )
        msg_payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": formatted_body
            }
        }
    else:
        # Default: Use Meta Approved WhatsApp Template (session_reminder)
        msg_payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": {
                "name": "session_reminder",
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": student_name},
                            {"type": "text", "text": course_name},
                            {"type": "text", "text": trainer_name},
                            {"type": "text", "text": session_time},
                            {"type": "text", "text": meeting_link}
                        ]
                    }
                ]
            }
        }

    print(f"Sending WhatsApp session notification to {recipient} ({student_name})...")
    resp = requests.post(whatsapp_url, headers=headers, json=msg_payload, timeout=30)
    print("Meta Status:", resp.status_code)
    print("Meta Response:", resp.text)

    try:
        resp_json = resp.json()
    except ValueError:
        resp_json = {"raw": resp.text}

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=resp_json)

    return {
        "status": "success",
        "phone_number": recipient,
        "student_name": student_name,
        "course_name": course_name,
        "meta_response": resp_json
    }


# =========================================================
# EXOTEL IVR + WABA INTEGRATION ENDPOINTS
# =========================================================

@app.api_route("/api/ivr/waba", methods=["GET", "POST"])
@app.api_route("/ivr/whatsapp", methods=["GET", "POST"])
async def exotel_ivr_waba_handler(request: Request):
    """
    Exotel Passthrough Applet Webhook Handler.
    Receives incoming IVR call event and dispatches automated WhatsApp message to the caller.
    Supports both HTTP GET (query parameters) and POST (form-data / JSON).
    """
    params = {}
    if request.method == "GET":
        params = dict(request.query_params)
    else:
        try:
            form_data = await request.form()
            params = dict(form_data)
        except Exception:
            try:
                params = await request.json()
            except Exception:
                params = dict(request.query_params)

    call_sid = params.get("CallSid") or params.get("call_sid") or ""
    caller_phone = (
        params.get("CallFrom")
        or params.get("call_from")
        or params.get("From")
        or params.get("from")
        or params.get("caller")
        or params.get("Caller")
        or params.get("phone_number")
        or ""
    )
    exophone = params.get("CallTo") or params.get("call_to") or params.get("To") or params.get("to") or ""
    digits = str(params.get("Digits") or params.get("digits") or "").strip()
    call_type = params.get("CallType") or params.get("call_type") or "completed"

    print(f"\n[Exotel IVR Webhook] Received call: CallSid={call_sid}, From={caller_phone}, Digits={digits}, CallType={call_type}")

    if not caller_phone:
        raise HTTPException(status_code=400, detail="Missing required 'From' caller phone number")

    recipient = _normalize_phone_number(caller_phone)

    # Contextual WhatsApp Message formulation based on IVR DTMF Digits
    if digits == "1":
        message_text = (
            "🌟 *Welcome to ChakoraHub!*\n\n"
            "Thank you for contacting our IVR support. Here are the details you requested:\n\n"
            "📝 *Course Registration*: https://www.chakorahub.com/registration\n"
            "📚 *Explore Syllabus & Tracks*: https://www.chakorahub.com/syllabus\n\n"
            "Need help? Simply reply to this WhatsApp message and our team will assist you!"
        )
    elif digits == "2":
        message_text = (
            "🚀 *ChakoraHub Career & Opportunities*\n\n"
            "Thank you for calling ChakoraHub! Here are the links for careers and internships:\n\n"
            "💼 *Apply for Open Positions*: https://www.chakorahub.com/apply\n"
            "🎓 *Internship Program*: https://www.chakorahub.com/internships\n"
            "🔍 *Track Application Status*: https://www.chakorahub.com/track-application\n\n"
            "Best regards,\nChakoraHub Careers Team"
        )
    elif digits == "3":
        message_text = (
            "🎫 *ChakoraHub Support & Helpdesk*\n\n"
            "We received your support inquiry via IVR.\n\n"
            "📌 *Student Support Portal*: https://www.chakorahub.com/tickets/student\n"
            "📌 *Employee Support Portal*: https://www.chakorahub.com/tickets/employee\n\n"
            "You can also reply directly with your issue and we will resolve it promptly."
        )
    else:
        message_text = (
            "👋 *Hello from ChakoraHub!*\n\n"
            "Thank you for reaching out to us via our IVR helpline.\n\n"
            "🌐 *Visit our Website*: https://www.chakorahub.com\n"
            "📚 *Courses*: https://www.chakorahub.com/syllabus\n"
            "📝 *Registration*: https://www.chakorahub.com/registration\n\n"
            "Feel free to reply to this message anytime to chat with an advisor!"
        )

    # Send WhatsApp Message (graceful fallback in dev/test if Meta token unconfigured)
    whatsapp_status = "sent"
    meta_response = None
    try:
        if WHATSAPP_TOKEN and PHONE_NUMBER_ID:
            meta_response = _send_whatsapp_text_message(recipient, message_text)
        else:
            print(f"[Exotel IVR Webhook] Mock WhatsApp send to {recipient} (Meta credentials not configured locally)")
            whatsapp_status = "simulated"
            meta_response = {"mock": True, "recipient": recipient, "message": message_text}
    except Exception as e:
        print(f"[Exotel IVR Webhook ERROR] Failed sending WhatsApp: {e}")
        whatsapp_status = f"error: {str(e)}"

    return {
        "status": "success",
        "call_sid": call_sid,
        "caller": recipient,
        "digits": digits,
        "whatsapp_status": whatsapp_status,
        "meta_response": meta_response
    }


@app.get("/api/ivr/waba/health")
def ivr_waba_health():
    """Healthcheck specifically for Exotel IVR webhook readiness."""
    return {
        "service": "exotel-ivr-waba",
        "status": "ready",
        "whatsapp_configured": bool(WHATSAPP_TOKEN and PHONE_NUMBER_ID)
    }


# ═══════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("waba_service:app", host="0.0.0.0", port=2500, reload=False)