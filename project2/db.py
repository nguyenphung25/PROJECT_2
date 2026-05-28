import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "parking-images")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def init_db():
    print("[INFO] Supabase connected")


def upload_image_to_supabase(image_path):
    file_name = os.path.basename(image_path)
    storage_path = f"detections/{file_name}"

    with open(image_path, "rb") as f:
        supabase.storage.from_(SUPABASE_BUCKET).upload(
            storage_path,
            f,
            {
                "content-type": "image/jpeg",
                "upsert": "true"
            }
        )

    public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(storage_path)

    return file_name, public_url


def save_image_detection(
    image_path,
    detected_plate=None,
    vehicle_type="unknown",
    confidence=0,
    detection_status="success",
    note=None,
    parking_session_id=None
):
    file_name, image_url = upload_image_to_supabase(image_path)

    data = {
        "file_name": file_name,
        "image_url": image_url,
        "detected_plate": detected_plate,
        "vehicle_type": vehicle_type,
        "confidence": confidence,
        "detection_status": detection_status,
        "note": note,
        "parking_session_id": parking_session_id,
    }

    result = supabase.table("image_detections").insert(data).execute()

    return result.data[0]


def find_vehicle_inside(plate_text):
    result = (
        supabase.table("parking_sessions")
        .select("*")
        .eq("plate_number", plate_text)
        .eq("status", "inside")
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None


def save_vehicle_in(plate_text, image_path, confidence=0):
    session_result = (
        supabase.table("parking_sessions")
        .insert({
            "plate_number": plate_text,
            "status": "inside"
        })
        .execute()
    )

    session = session_result.data[0]

    detection = save_image_detection(
        image_path=image_path,
        detected_plate=plate_text,
        vehicle_type="unknown",
        confidence=confidence,
        detection_status="success",
        note="Xe vào - biển số hợp lệ",
        parking_session_id=session["id"]
    )

    supabase.table("parking_sessions").update({
        "entry_image_url": detection["image_url"]
    }).eq("id", session["id"]).execute()

    return session, detection


def save_vehicle_out(plate_text, image_path, confidence=0):
    session = find_vehicle_inside(plate_text)

    if session is None:
        return None, None

    detection = save_image_detection(
        image_path=image_path,
        detected_plate=plate_text,
        vehicle_type="unknown",
        confidence=confidence,
        detection_status="success",
        note="Xe ra - biển số hợp lệ",
        parking_session_id=session["id"]
    )

    supabase.table("parking_sessions").update({
        "exit_time": "now()",
        "exit_image_url": detection["image_url"],
        "status": "exited"
    }).eq("id", session["id"]).execute()

    return session, detection


def save_failed_detection(image_path, plate_text="", note="Nhận diện thất bại"):
    return save_image_detection(
        image_path=image_path,
        detected_plate=plate_text,
        vehicle_type="unknown",
        confidence=0,
        detection_status="failed",
        note=note,
        parking_session_id=None
    )


def get_latest_detections(limit=10):
    result = (
        supabase.table("image_detections")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return result.data