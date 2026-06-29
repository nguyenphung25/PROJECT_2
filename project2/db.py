import uuid
import os
import re
from datetime import datetime, timedelta
from supabase import create_client

# Load Supabase credentials from .env
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "parking-images")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise Exception("Thieu SUPABASE_URL hoac SUPABASE_SERVICE_KEY trong file .env")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

SERVER_BASE_URL = "http://localhost:5000"


def is_valid_plate(plate_text):
    """Kiem tra bien so hop le: 2 so + 1 chu + 5 so. VD: 60A22345, 89D62446"""
    if not plate_text:
        return False
    plate_text = plate_text.upper().replace("-", "").replace(".", "").replace(" ", "")
    return re.match(r"^[0-9]{2}[A-Z][0-9]{5}$", plate_text) is not None


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def image_url_from_path(image_path):
    if not image_path:
        return ""

    image_path = image_path.replace("\\", "/")
    return f"{SERVER_BASE_URL}/{image_path}"


def init_db():
    """Kiem tra ket noi Supabase"""
    try:
        # Test connection by querying parking_sessions
        supabase.table("parking_sessions").select("id").limit(1).execute()
        print("[DB] Supabase ket noi thanh cong!")
        print(f"[DB] URL: {SUPABASE_URL}")
        print(f"[DB] Bucket: {SUPABASE_BUCKET}")
    except Exception as e:
        print(f"[DB ERROR] Khong ket noi duoc Supabase: {e}")
        raise


def upload_image_bytes(image_bytes, filename, folder="full"):
    """
    Upload anh bang bytes truc tiep len Supabase Storage.
    Khong luu file local.
    """
    try:
        path = f"{folder}/{filename}"

        try:
            supabase.storage.from_(SUPABASE_BUCKET).remove([path])
        except Exception:
            pass

        result = supabase.storage.from_(SUPABASE_BUCKET).upload(
            path=path,
            file=image_bytes,
            file_options={"content-type": "image/jpeg"}
        )

        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(path)
        print(f"[UPLOAD] {path} -> {public_url}")
        return public_url

    except Exception as e:
        print(f"[UPLOAD ERROR] Khong upload duoc {filename}: {e}")
        return None


def upload_image(file_path, folder="full"):
    """
    Upload anh len Supabase Storage va tra ve public URL.
    folder: 'full' cho anh toan canh, 'crops' cho anh cat bien so
    """
    if not file_path or not os.path.exists(file_path):
        return None

    try:
        # Tao ten file duy nhat
        filename = f"{folder}/{os.path.basename(file_path)}"

        # Doc file
        with open(file_path, "rb") as f:
            file_data = f.read()

        # Xoa file cu neu da ton tai (ignore error)
        try:
            supabase.storage.from_(SUPABASE_BUCKET).remove([filename])
        except Exception:
            pass

        # Upload len Supabase Storage
        result = supabase.storage.from_(SUPABASE_BUCKET).upload(
            path=filename,
            file=file_data,
            file_options={"content-type": "image/jpeg"}
        )

        # Lay public URL
        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(filename)

        print(f"[UPLOAD] {filename} -> {public_url}")
        return public_url

    except Exception as e:
        print(f"[UPLOAD ERROR] Khong upload duoc {file_path}: {e}")
        return None


def find_vehicle_inside(plate_text):
    result = (
        supabase.table("parking_sessions")
        .select("*")
        .eq("plate_text", plate_text)
        .eq("status", "inside")
        .order("entry_time", desc=True)
        .limit(1)
        .execute()
    )

    if result.data and len(result.data) > 0:
        return result.data[0]
    return None


def save_vehicle_in(plate_text, image_path, confidence=0):
    if not is_valid_plate(plate_text):
        raise Exception(f"Bien so khong hop le: '{plate_text}'. Chi luu bien so hop le (VD: 60A22345).")

    current_time = now_text()

    # Kiem tra xe da o trong bai chua
    existing_result = (
        supabase.table("parking_sessions")
        .select("*")
        .eq("plate_text", plate_text)
        .eq("status", "inside")
        .order("entry_time", desc=True)
        .limit(1)
        .execute()
    )

    if existing_result.data and len(existing_result.data) > 0:
        existing_session = existing_result.data[0]
        session_id = existing_session["id"]

        detection_id = str(uuid.uuid4())

        detection_data = {
            "id": detection_id,
            "parking_session_id": session_id,
            "action": "entry",
            "plate_text": plate_text,
            "image_path": image_path,
            "image_url": image_path,
            "confidence": confidence,
            "detection_status": "success",
            "note": "Xe da co trong bai",
            "created_at": current_time
        }

        supabase.table("detections").insert(detection_data).execute()

        # Lay detection vua insert
        det_result = (
            supabase.table("detections")
            .select("*")
            .eq("id", detection_id)
            .limit(1)
            .execute()
        )
        detection = det_result.data[0] if det_result.data else detection_data

        return existing_session, detection

    # Tao phien gui xe moi
    session_id = str(uuid.uuid4())
    detection_id = str(uuid.uuid4())

    session_data = {
        "id": session_id,
        "plate_text": plate_text,
        "entry_time": current_time,
        "exit_time": None,
        "entry_image_path": image_path,
        "exit_image_path": None,
        "status": "inside",
        "created_at": current_time,
        "updated_at": current_time
    }

    supabase.table("parking_sessions").insert(session_data).execute()

    detection_data = {
        "id": detection_id,
        "parking_session_id": session_id,
        "action": "entry",
        "plate_text": plate_text,
        "image_path": image_path,
        "image_url": image_path,
        "confidence": confidence,
        "detection_status": "success",
        "note": "Xe vao bai",
        "created_at": current_time
    }

    supabase.table("detections").insert(detection_data).execute()

    # Lay du lieu vua insert
    session_result = (
        supabase.table("parking_sessions")
        .select("*")
        .eq("id", session_id)
        .limit(1)
        .execute()
    )
    session = session_result.data[0] if session_result.data else session_data

    det_result = (
        supabase.table("detections")
        .select("*")
        .eq("id", detection_id)
        .limit(1)
        .execute()
    )
    detection = det_result.data[0] if det_result.data else detection_data

    return session, detection


def save_vehicle_out(plate_text, image_path, confidence=0):
    if not is_valid_plate(plate_text):
        raise Exception(f"Bien so khong hop le: '{plate_text}'. Chi luu bien so hop le (VD: 60A22345).")

    current_time = now_text()

    # Tim xe dang o trong bai
    session_result = (
        supabase.table("parking_sessions")
        .select("*")
        .eq("plate_text", plate_text)
        .eq("status", "inside")
        .order("entry_time", desc=True)
        .limit(1)
        .execute()
    )

    if not session_result.data or len(session_result.data) == 0:
        raise Exception("Khong tim thay xe trong bai")

    session_row = session_result.data[0]
    session_id = session_row["id"]
    detection_id = str(uuid.uuid4())

    # Cap nhat parking_session
    supabase.table("parking_sessions").update({
        "exit_time": current_time,
        "exit_image_path": image_path,
        "status": "exited",
        "updated_at": current_time
    }).eq("id", session_id).execute()

    # Tao detection moi
    detection_data = {
        "id": detection_id,
        "parking_session_id": session_id,
        "action": "exit",
        "plate_text": plate_text,
        "image_path": image_path,
        "image_url": image_path,
        "confidence": confidence,
        "detection_status": "success",
        "note": "Xe ra khoi bai",
        "created_at": current_time
    }

    supabase.table("detections").insert(detection_data).execute()

    # Lay du lieu vua update/insert
    session_result = (
        supabase.table("parking_sessions")
        .select("*")
        .eq("id", session_id)
        .limit(1)
        .execute()
    )
    session = session_result.data[0] if session_result.data else session_row

    det_result = (
        supabase.table("detections")
        .select("*")
        .eq("id", detection_id)
        .limit(1)
        .execute()
    )
    detection = det_result.data[0] if det_result.data else detection_data

    return session, detection


def save_failed_detection(image_path, plate_text="", note=""):
    detection_id = str(uuid.uuid4())
    current_time = now_text()

    detection_data = {
        "id": detection_id,
        "parking_session_id": None,
        "action": "unknown",
        "plate_text": plate_text,
        "image_path": image_path,
        "image_url": image_path,
        "confidence": 0,
        "detection_status": "failed",
        "note": note,
        "created_at": current_time
    }

    supabase.table("detections").insert(detection_data).execute()

    det_result = (
        supabase.table("detections")
        .select("*")
        .eq("id", detection_id)
        .limit(1)
        .execute()
    )
    detection = det_result.data[0] if det_result.data else detection_data

    return detection


def get_latest_detections(limit=10):
    result = (
        supabase.table("detections")
        .select("id, parking_session_id, action, plate_text, image_path, image_url, confidence, detection_status, note, created_at, parking_sessions!inner(entry_time, exit_time, status)")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    if not result.data:
        return []

    # Chuyen doi nested data
    detections = []
    for row in result.data:
        session_info = row.pop("parking_sessions", {})
        row["entry_time"] = session_info.get("entry_time") if session_info else None
        row["exit_time"] = session_info.get("exit_time") if session_info else None
        row["status"] = session_info.get("status") if session_info else None
        detections.append(row)

    return detections


def count_vehicles_inside():
    result = (
        supabase.table("parking_sessions")
        .select("id", count="exact")
        .eq("status", "inside")
        .execute()
    )

    return result.count if result.count is not None else 0


def get_latest_sessions(limit=10):
    result = (
        supabase.table("parking_sessions")
        .select("id, plate_text, entry_time, exit_time, status, entry_image_path, exit_image_path, created_at, updated_at")
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )

    return result.data if result.data else []


def get_sessions_last_24h():
    # Tinh thoi gian 24h truoc
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

    result = (
        supabase.table("parking_sessions")
        .select("id, plate_text, entry_time, exit_time, status, entry_image_path, exit_image_path, created_at, updated_at")
        .gte("updated_at", yesterday)
        .order("updated_at", desc=True)
        .execute()
    )

    return result.data if result.data else []
