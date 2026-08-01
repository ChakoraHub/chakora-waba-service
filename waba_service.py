from fastapi import FastAPI, HTTPException
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
    
# ═══════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("waba_service:app", host="0.0.0.0", port=2500, reload=False)