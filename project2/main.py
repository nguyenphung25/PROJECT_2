import os
import cv2
import time
import re
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
import uuid
import threading

from detect_plate import PlateDetector
from ocr_plate import PlateOCR
from db import (
    init_db,
    save_vehicle_in,
    save_vehicle_out,
    find_vehicle_inside,
    save_failed_detection,
    get_latest_detections,
    get_latest_sessions,
    get_sessions_last_24h,
    count_vehicles_inside,
    upload_image,
    upload_image_bytes
)

app = Flask(__name__)

CORS(app)
detector = None
ocr = None
cap = None
SERVER_BASE_URL = "http://localhost:5000"

last_event = {
    "entry": None,
    "exit": None
}
pending_manual = {}
pending_lock = threading.Lock()
camera_lock = threading.Lock()  # Lock cho webcam, tranh race condition

# Co reset ESP32: khi web UI bấm Reset, flag này được bật.
# ESP32 sẽ poll endpoint /esp32/check-reset để nhận lệnh reset.
reset_flag = {"requested": False}
reset_flag_lock = threading.Lock()

MANUAL_WAIT_SECONDS = 25
MAX_RECOGNITION_ATTEMPTS = 2

#thêm hàm hỗ trợ 
def image_url_from_path(image_path):
    if not image_path:
        return ""

    image_path = image_path.replace("\\", "/")

    return f"{SERVER_BASE_URL}/{image_path}"


def set_last_event(event):
    global last_event

    if not event:
        return

    action = event.get("action")

    if action == "entry":
        last_event["entry"] = event
        last_event["exit"] = None

    elif action == "exit":
        last_event["exit"] = event
        last_event["entry"] = None

def create_pending_manual(action, image_path, message, plate_text=""):
    pending_id = str(uuid.uuid4())

    event = threading.Event()

    pending_data = {
        "pending_id": pending_id,
        "action": action,
        "image_path": image_path,
        "image_url": image_url_from_path(image_path),
        "message": message,
        "plate_text": plate_text,
        "manual_required": True,
        "allow": False,
        "event": event,
        "result": None
    }

    with pending_lock:
        pending_manual[pending_id] = pending_data

    set_last_event({
        "pending_id": pending_id,
        "action": action,
        "image_path": image_path,
        "image_url": image_url_from_path(image_path),
        "message": message,
        "plate_text": plate_text,
        "manual_required": True,
        "allow": False
    })

    return pending_id


def wait_manual_result(pending_id):
    with pending_lock:
        pending = pending_manual.get(pending_id)

    if pending is None:
        return None

    pending["event"].wait(MANUAL_WAIT_SECONDS)

    with pending_lock:
        pending = pending_manual.pop(pending_id, None)

    if pending is None:
        return None

    return pending.get("result")


def normalize_manual_plate(plate_text):
    raw = clean_plate_text(plate_text)

    if not is_valid_plate(raw):
        return None, raw

    return format_plate_text(raw), raw



def clean_plate_text(text):
    if text is None:
        return ""

    text = text.upper()
    text = re.sub(r"[^A-Z0-9]", "", text)

    return text

def format_plate_text(plate_text):
    """
    Format biển số:
    60A22345 -> 60A-223.45
    89D62446 -> 89D-624.46
    """
    plate_text = clean_plate_text(plate_text)

    # Biển số dạng: 2 số tỉnh + 1 chữ seri + 5 số
    # VD: 60A22345
    if len(plate_text) == 8:
        province = plate_text[:2]   # 60
        series = plate_text[2]      # A
        number = plate_text[3:]     # 22345

        number = number[:3] + "." + number[3:]

        return f"{province}{series}-{number}"

    return plate_text
def is_valid_plate(plate_text):
    """
    Biển hợp lệ dạng:
    2 số + 1 chữ + 5 số
    VD: 23A23221, 89D62446, 60A22345
    """
    plate_text = clean_plate_text(plate_text)

    pattern = r"^[0-9]{2}[A-Z][0-9]{5}$"

    return re.match(pattern, plate_text) is not None

def capture_frame(prefix):
    global cap

    if cap is None or not cap.isOpened():
        raise Exception("Webcam chua duoc mo")

    with camera_lock:
        # Warmup: doc 5 frame de webcam on dinh
        for _ in range(5):
            cap.read()

        ret, frame = cap.read()

    if not ret or frame is None:
        raise Exception("Khong doc duoc frame tu webcam")

    timestamp = int(time.time())
    filename = f"{prefix}_{timestamp}.jpg"

    # Luu anh local truoc de recognize_plate() co the doc duoc
    os.makedirs("test_images", exist_ok=True)
    local_path = os.path.join("test_images", filename)
    cv2.imwrite(local_path, frame)
    print(f"[INFO] Anh da luu local: {local_path}")

    # Upload len Supabase
    _, buffer = cv2.imencode(".jpg", frame)
    image_bytes = buffer.tobytes()
    image_url = upload_image_bytes(image_bytes, filename, folder="full")

    # Tra ve ca local_path (de recognize_plate doc) va image_url (de hien thi web)
    # Va ca frame array (de truc tiep dung cho detect)
    return local_path, image_url, frame


def recognize_plate(image_input):
    """
    Nhan dien bien so tu anh.
    image_input: duong dan file HOAC numpy array (BGR).
    """
    crop_arrays, crop_urls, plate_boxes = detector.crop_plates(image_input)

    if not crop_arrays:
        return {
            "valid": False,
            "plate_text": "",
            "message": "Khong phat hien bien so"
        }

    best_result = None

    for crop_array, crop_url, box in zip(crop_arrays, crop_urls, plate_boxes):
        plate_text, ocr_conf = ocr.read_plate_image(crop_array)

        plate_text = clean_plate_text(plate_text)

        print("Anh:", image_input if isinstance(image_input, str) else "numpy_array")
        print("Crop URL:", crop_url)
        print("Bien so doc duoc:", plate_text)
        print("Detect conf:", box["confidence"])
        print("OCR conf:", ocr_conf)
        print("-" * 50)

        if best_result is None or ocr_conf > best_result["ocr_conf"]:
            best_result = {
                "plate_text": plate_text,
                "detect_conf": float(box["confidence"]),
                "ocr_conf": float(ocr_conf),
                "crop_url": crop_url
            }

    if best_result is None:
        return {
            "valid": False,
            "plate_text": "",
            "message": "Khong doc duoc bien so"
        }

    raw_plate_text = best_result["plate_text"]

    if not is_valid_plate(raw_plate_text):
        return {
            "valid": False,
            "plate_text": raw_plate_text,
            "message": "Bien so khong hop le"
        }

    formatted_plate_text = format_plate_text(raw_plate_text)

    print("Bien so goc:", raw_plate_text)
    print("Bien so sau format:", formatted_plate_text)

    return {
        "valid": True,
        "plate_text": formatted_plate_text,
        "raw_plate_text": raw_plate_text,
        "detect_conf": best_result["detect_conf"],
        "ocr_conf": best_result["ocr_conf"],
        "crop_url": best_result.get("crop_url"),
        "message": "Bien so hop le"
    }


def scan_plate_with_retries(action, prefix):
    last_local_path = ""
    last_full_image_url = ""
    last_result = {
        "valid": False,
        "plate_text": "",
        "message": "Khong nhan dien duoc bien so"
    }

    for attempt in range(1, MAX_RECOGNITION_ATTEMPTS + 1):
        set_last_event({
            "action": action,
            "processing": True,
            "message": f"Dang nhan dien bien so... Lan {attempt}/{MAX_RECOGNITION_ATTEMPTS}",
            "allow": False,
            "manual_required": False
        })

        time.sleep(1)

        local_path, full_image_url, frame = capture_frame(prefix)
        result = recognize_plate(frame)

        last_local_path = local_path
        last_full_image_url = full_image_url
        last_result = result

        if result["valid"]:
            return local_path, full_image_url, result

        print(f"[INFO] Lan quet {attempt}/{MAX_RECOGNITION_ATTEMPTS} khong nhan dien duoc: {result['message']}")

    last_result["message"] = (
        f"Da quet {MAX_RECOGNITION_ATTEMPTS} lan nhung khong nhan dien duoc bien so. "
        "Vui long nhap tay."
    )

    return last_local_path, last_full_image_url, last_result

#Route để web xem được ảnh vừa chụp
@app.route("/test_images/<path:filename>", methods=["GET"])
def serve_test_image(filename):
    return send_from_directory("test_images", filename)

#Thêm route để lấy trạng thái mới nhất cho web
@app.route("/state/latest", methods=["GET"])
def state_latest():
    return jsonify({
        "success": True,
        "data": last_event
    })

#Thêm route xác nhận biển số nhập tay
@app.route("/manual/confirm", methods=["POST"])
def manual_confirm():
    try:
        data = request.get_json(force=True)

        pending_id = data.get("pending_id")
        plate_input = data.get("plate_text", "")

        if not pending_id:
            return jsonify({
                "success": False,
                "message": "Thieu pending_id"
            }), 400

        plate_text, raw_plate = normalize_manual_plate(plate_input)

        if plate_text is None:
            return jsonify({
                "success": False,
                "message": "Bien so nhap tay khong hop le. VD dung: 30A12345"
            }), 200

        with pending_lock:
            pending = pending_manual.get(pending_id)

        if pending is None:
            return jsonify({
                "success": False,
                "message": "Phien nhap tay da het han"
            }), 404

        action = pending["action"]
        image_path = pending["image_path"]

        if action == "entry":
            # Kiem tra xe da o trong bai chua
            existing = find_vehicle_inside(plate_text)
            if existing is not None:
                return jsonify({
                    "success": False,
                    "message": f"Xe {plate_text} da co trong bai, khong cho vao lan nua"
                }), 200

            session, detection = save_vehicle_in(
                plate_text=plate_text,
                image_path=image_path,
                confidence=1
            )

            result_event = {
                "allow": True,
                "action": "entry",
                "plate_text": plate_text,
                "raw_plate_text": raw_plate,
                "message": "Nhap tay thanh cong, cho xe vao",
                "image_path": image_path,
                "image_url": detection.get("image_url") or image_url_from_path(image_path),
                "detection_id": detection["id"],
                "parking_session_id": session["id"],
                "manual_required": False
            }

        elif action == "exit":
            vehicle = find_vehicle_inside(plate_text)

            if vehicle is None:
                return jsonify({
                    "success": False,
                    "message": "Bien so khong co trong database xe dang o trong bai"
                }), 200

            session, detection = save_vehicle_out(
                plate_text=plate_text,
                image_path=image_path,
                confidence=1
            )

            result_event = {
                "allow": True,
                "action": "exit",
                "plate_text": plate_text,
                "raw_plate_text": raw_plate,
                "message": "Nhap tay thanh cong, cho xe ra",
                "image_path": image_path,
                "image_url": detection.get("image_url") or image_url_from_path(image_path),
                "detection_id": detection["id"],
                "parking_session_id": session["id"],
                "manual_required": False
            }

        else:
            return jsonify({
                "success": False,
                "message": "Action khong hop le"
            }), 400

        pending["result"] = result_event
        pending["event"].set()

        set_last_event(result_event)

        return jsonify({
            "success": True,
            "event": result_event
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
    

@app.route("/", methods=["GET"])
def home():
    return "Parking webcam server is running"
def generate_camera_stream():
    global cap

    while True:
        if cap is None or not cap.isOpened():
            time.sleep(0.1)
            continue

        with camera_lock:
            ret, frame = cap.read()

        if not ret or frame is None:
            time.sleep(0.1)
            continue

        frame = cv2.resize(frame, (640, 360))

        ret, buffer = cv2.imencode(".jpg", frame)

        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )
@app.route("/state/reset", methods=["POST"])
def reset_state():
    global last_event

    last_event = {
        "entry": None,
        "exit": None
    }

    # Bật cờ reset để ESP32 nhận lệnh reset LCD + state machine
    with reset_flag_lock:
        reset_flag["requested"] = True

    return jsonify({
        "success": True,
        "message": "Da reset trang thai giao dien"
    }), 200


@app.route("/esp32/check-reset", methods=["GET"])
def esp32_check_reset():
    """ESP32 poll endpoint này để kiểm tra có lệnh reset từ web UI không."""
    with reset_flag_lock:
        if reset_flag["requested"]:
            reset_flag["requested"] = False
            return jsonify({"reset": True}), 200

    return jsonify({"reset": False}), 200


@app.route("/esp32/vehicle-passed", methods=["GET"])
def esp32_vehicle_passed():
    """ESP32 goi endpoint nay khi xe di qua IR sensor.
    Clear anh plate tren Web UI va reset trang thai."""
    global last_event
    last_event = {"entry": None, "exit": None}
    print("[INFO] Xe da di qua IR - Reset Web UI")
    return jsonify({"success": True, "reset": True}), 200


@app.route("/esp32/sync", methods=["GET"])
def esp32_sync():
    """ESP32 poll endpoint nay de dong bo vehicle count va gate status.
    Giup LCD cap nhat khi web UI da xu ly xe vao/ra."""
    try:
        inside = count_vehicles_inside()

        return jsonify({
            "success": True,
            "vehicles_inside": inside,
            "gate_status": "Closed"
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route("/video_feed", methods=["GET"])
def video_feed():
    return Response(
        generate_camera_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/entry", methods=["GET"])
def entry():
    try:
        print("[INFO] Xe vao - Nhan tin hieu tu ESP32")

        # Thong bao web UI ngay lap tuc: camera dang xu ly
        set_last_event({
            "action": "entry",
            "processing": True,
            "message": "Dang nhan dien bien so...",
            "allow": False,
            "manual_required": False
        })

        local_path, full_image_url, result = scan_plate_with_retries("entry", "entry")

        if not result["valid"]:
            pending_id = create_pending_manual(
                action="entry",
                image_path=local_path,
                message=result["message"],
                plate_text=result.get("plate_text", "")
            )

            manual_result = wait_manual_result(pending_id)

            if manual_result is not None and manual_result.get("allow"):
                return jsonify(manual_result), 200

            try:
                save_failed_detection(
                    image_path=full_image_url or local_path,
                    plate_text=result.get("plate_text", ""),
                    note=result["message"]
                )
            except Exception as db_error:
                print("[DB ERROR]", str(db_error))

            timeout_event = {
                "allow": False,
                "action": "entry",
                "message": "Het thoi gian nhap tay, khong mo barrier",
                "plate_text": result.get("plate_text", ""),
                "image_path": local_path,
                "image_url": full_image_url or image_url_from_path(local_path),
                "manual_required": False
            }

            set_last_event(timeout_event)

            return jsonify(timeout_event), 200

        plate_text = result["plate_text"]

        # Kiem tra xe da o trong bai chua - neu roi thi yeu cau nhap lai thu cong
        existing = find_vehicle_inside(plate_text)
        if existing is not None:
            print(f"[INFO] Xe {plate_text} da co trong bai - Yeu cau nhap lai")
            pending_id = create_pending_manual(
                action="entry",
                image_path=local_path,
                message=f"Xe {plate_text} da co trong database. Vui long nhap lai bien so.",
                plate_text=plate_text
            )

            manual_result = wait_manual_result(pending_id)

            if manual_result is not None and manual_result.get("allow"):
                return jsonify(manual_result), 200

            try:
                save_failed_detection(
                    image_path=full_image_url or local_path,
                    plate_text=plate_text,
                    note="Xe da co trong database khi vao"
                )
            except Exception as db_error:
                print("[DB ERROR]", str(db_error))

            timeout_event = {
                "allow": False,
                "action": "entry",
                "plate_text": plate_text,
                "message": f"Xe {plate_text} da co trong database, khong mo barrier",
                "image_path": local_path,
                "image_url": full_image_url or image_url_from_path(local_path),
                "manual_required": False
            }
            set_last_event(timeout_event)
            return jsonify(timeout_event), 200

        response_data = {
            "allow": True,
            "action": "entry",
            "plate_text": plate_text,
            "message": "Bien so hop le, cho xe vao",
            "image_path": local_path,
            "image_url": full_image_url or image_url_from_path(local_path),
            "manual_required": False
        }

        try:
            session, detection = save_vehicle_in(
                plate_text=plate_text,
                image_path=full_image_url or local_path,
                confidence=result.get("ocr_conf", 0)
            )

            response_data["image_url"] = detection.get("image_url") or full_image_url or image_url_from_path(local_path)
            response_data["detection_id"] = detection["id"]
            response_data["parking_session_id"] = session["id"]

        except Exception as db_error:
            print("[DB ERROR]", str(db_error))
            response_data["message"] = "Cho xe vao, nhung chua luu duoc database"
            response_data["db_error"] = str(db_error)

        set_last_event(response_data)

        return jsonify(response_data), 200

    except Exception as e:
        print("[ERROR]", str(e))
        return jsonify({
            "allow": False,
            "action": "entry",
            "message": str(e),
            "manual_required": False
        }), 500

@app.route("/exit", methods=["GET"])
def exit_parking():
    try:
        print("[INFO] Xe ra - Nhan tin hieu tu ESP32")

        # Thong bao web UI ngay lap tuc: camera dang xu ly
        set_last_event({
            "action": "exit",
            "processing": True,
            "message": "Dang nhan dien bien so...",
            "allow": False,
            "manual_required": False
        })

        local_path, full_image_url, result = scan_plate_with_retries("exit", "exit")

        if not result["valid"]:
            pending_id = create_pending_manual(
                action="exit",
                image_path=local_path,
                message=result["message"],
                plate_text=result.get("plate_text", "")
            )

            manual_result = wait_manual_result(pending_id)

            if manual_result is not None and manual_result.get("allow"):
                return jsonify(manual_result), 200

            try:
                save_failed_detection(
                    image_path=full_image_url or local_path,
                    plate_text=result.get("plate_text", ""),
                    note=result["message"]
                )
            except Exception as db_error:
                print("[DB ERROR]", str(db_error))

            timeout_event = {
                "allow": False,
                "action": "exit",
                "message": "Het thoi gian nhap tay, khong mo barrier",
                "plate_text": result.get("plate_text", ""),
                "image_path": local_path,
                "image_url": full_image_url or image_url_from_path(local_path),
                "manual_required": False
            }

            set_last_event(timeout_event)

            return jsonify(timeout_event), 200

        plate_text = result["plate_text"]

        vehicle = find_vehicle_inside(plate_text)

        if vehicle is None:
            pending_id = create_pending_manual(
                action="exit",
                image_path=local_path,
                message="Bien so nhan dien duoc nhung khong co trong database. Vui long nhap lai thu cong.",
                plate_text=plate_text
            )

            manual_result = wait_manual_result(pending_id)

            if manual_result is not None and manual_result.get("allow"):
                return jsonify(manual_result), 200

            try:
                save_failed_detection(
                    image_path=full_image_url or local_path,
                    plate_text=plate_text,
                    note="Khong tim thay xe trong database"
                )
            except Exception as db_error:
                print("[DB ERROR]", str(db_error))

            timeout_event = {
                "allow": False,
                "action": "exit",
                "plate_text": plate_text,
                "message": "Khong tim thay xe trong database, khong mo barrier",
                "image_path": local_path,
                "image_url": full_image_url or image_url_from_path(local_path),
                "manual_required": False
            }

            set_last_event(timeout_event)

            return jsonify(timeout_event), 200

        response_data = {
            "allow": True,
            "action": "exit",
            "plate_text": plate_text,
            "message": "Bien so hop le, cho xe ra",
            "image_path": local_path,
            "image_url": full_image_url or image_url_from_path(local_path),
            "manual_required": False
        }

        try:
            session, detection = save_vehicle_out(
                plate_text=plate_text,
                image_path=full_image_url or local_path,
                confidence=result.get("ocr_conf", 0)
            )

            response_data["image_url"] = detection.get("image_url") or full_image_url or image_url_from_path(local_path)
            response_data["detection_id"] = detection["id"]
            response_data["parking_session_id"] = session["id"]

        except Exception as db_error:
            print("[DB ERROR]", str(db_error))
            response_data["message"] = "Cho xe ra, nhung chua luu duoc database"
            response_data["db_error"] = str(db_error)

        set_last_event(response_data)

        return jsonify(response_data), 200

    except Exception as e:
        print("[ERROR]", str(e))
        return jsonify({
            "allow": False,
            "action": "exit",
            "message": str(e),
            "manual_required": False
        }), 500
@app.route("/detections/latest", methods=["GET"])
def latest_detections():
    try:
        detections = get_latest_detections(10)

        return jsonify({
            "success": True,
            "data": detections
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e),
            "data": []
        }), 500

@app.route("/sessions/latest", methods=["GET"])
def latest_sessions():
    try:
        sessions = get_latest_sessions(10)

        return jsonify({
            "success": True,
            "data": sessions
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e),
            "data": []
        }), 500


@app.route("/sessions/24h", methods=["GET"])
def sessions_24h():
    try:
        sessions = get_sessions_last_24h()

        return jsonify({
            "success": True,
            "data": sessions
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e),
            "data": []
        }), 500

def start_server():
    global detector, ocr, cap

    init_db()

    detector = PlateDetector("models/best.pt")
    ocr = PlateOCR()

    CAMERA_INDEX = 1  # webcam ngoài

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print(f"[ERROR] Khong mo duoc webcam {CAMERA_INDEX}")
        return

    print(f"[INFO] Dang dung webcam index {CAMERA_INDEX}")
    print("[INFO] Parking webcam server dang chay")
    print("[INFO] Entry: http://localhost:5000/entry")
    print("[INFO] Exit : http://localhost:5000/exit")

    app.run(host="0.0.0.0", port=5000, threaded=True)

if __name__ == "__main__":
    start_server()
