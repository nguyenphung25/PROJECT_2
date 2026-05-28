import os
import cv2
import time
import re
from flask import Flask, jsonify
from flask_cors import CORS

from detect_plate import PlateDetector
from ocr_plate import PlateOCR
from db import (
    init_db,
    save_vehicle_in,
    save_vehicle_out,
    find_vehicle_inside,
    save_failed_detection,
    get_latest_detections
)

app = Flask(__name__)

CORS(app)
detector = None
ocr = None
cap = None


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

    for _ in range(5):
        ret, frame = cap.read()

    ret, frame = cap.read()

    if not ret:
        raise Exception("Khong doc duoc frame tu webcam")

    os.makedirs("test_images", exist_ok=True)

    timestamp = int(time.time())
    image_path = f"test_images/{prefix}_{timestamp}.jpg"

    cv2.imwrite(image_path, frame)

    return image_path


def recognize_plate(image_path):
    crop_paths, plate_boxes = detector.crop_plates(image_path)

    if not crop_paths:
        return {
            "valid": False,
            "plate_text": "",
            "message": "Khong phat hien bien so"
        }

    best_result = None

    for crop_path, box in zip(crop_paths, plate_boxes):
        plate_text, ocr_conf = ocr.read_plate(crop_path)

        plate_text = clean_plate_text(plate_text)

        print("Anh:", image_path)
        print("Crop:", crop_path)
        print("Bien so doc duoc:", plate_text)
        print("Detect conf:", box["confidence"])
        print("OCR conf:", ocr_conf)
        print("-" * 50)

        if best_result is None or ocr_conf > best_result["ocr_conf"]:
            best_result = {
                "plate_text": plate_text,
                "detect_conf": float(box["confidence"]),
                "ocr_conf": float(ocr_conf),
                "crop_path": crop_path
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
        "crop_path": best_result["crop_path"],
        "message": "Bien so hop le"
    }


@app.route("/", methods=["GET"])
def home():
    return "Parking webcam server is running"


@app.route("/entry", methods=["GET"])
def entry():
    try:
        print("[INFO] Xe vao - Nhan tin hieu tu ESP32")

        time.sleep(1)

        image_path = capture_frame("entry")
        result = recognize_plate(image_path)

        if not result["valid"]:
            return jsonify({
                "allow": False,
                "action": "entry",
                "message": result["message"],
                "plate_text": result.get("plate_text", ""),
                "image_path": image_path
            }), 200

        plate_text = result["plate_text"]

        response_data = {
            "allow": True,
            "action": "entry",
            "plate_text": plate_text,
            "message": "Bien so hop le, cho xe vao",
            "image_path": image_path
        }

        try:
            session, detection = save_vehicle_in(
                plate_text=plate_text,
                image_path=image_path,
                confidence=result.get("ocr_conf", 0)
            )

            response_data["image_url"] = detection["image_url"]
            response_data["detection_id"] = detection["id"]
            response_data["parking_session_id"] = session["id"]

        except Exception as db_error:
            print("[DB ERROR]", str(db_error))
            response_data["message"] = "Cho xe vao, nhung chua luu duoc database"
            response_data["db_error"] = str(db_error)

        return jsonify(response_data), 200

    except Exception as e:
        print("[ERROR]", str(e))
        return jsonify({
            "allow": False,
            "action": "entry",
            "message": str(e)
        }), 500
@app.route("/exit", methods=["GET"])
def exit_parking():
    try:
        print("[INFO] Xe ra - Nhan tin hieu tu ESP32")

        time.sleep(1)

        image_path = capture_frame("exit")
        result = recognize_plate(image_path)

        if not result["valid"]:
            return jsonify({
                "allow": False,
                "action": "exit",
                "message": result["message"],
                "plate_text": result.get("plate_text", ""),
                "image_path": image_path
            }), 200

        plate_text = result["plate_text"]

        response_data = {
            "allow": True,
            "action": "exit",
            "plate_text": plate_text,
            "message": "Bien so hop le, cho xe ra",
            "image_path": image_path
        }

        try:
            vehicle = find_vehicle_inside(plate_text)

            if vehicle is None:
                return jsonify({
                    "allow": False,
                    "action": "exit",
                    "plate_text": plate_text,
                    "message": "Khong tim thay xe trong database",
                    "image_path": image_path
                }), 200

            session, detection = save_vehicle_out(
                plate_text=plate_text,
                image_path=image_path,
                confidence=result.get("ocr_conf", 0)
            )

            response_data["image_url"] = detection["image_url"]
            response_data["detection_id"] = detection["id"]
            response_data["parking_session_id"] = session["id"]

        except Exception as db_error:
            print("[DB ERROR]", str(db_error))
            response_data["message"] = "Cho xe ra, nhung chua luu duoc database"
            response_data["db_error"] = str(db_error)

        return jsonify(response_data), 200

    except Exception as e:
        print("[ERROR]", str(e))
        return jsonify({
            "allow": False,
            "action": "exit",
            "message": str(e)
        }), 500
    try:
        print("[INFO] Xe ra - Nhan tin hieu tu ESP32")

        time.sleep(1)

        image_path = capture_frame("exit")
        result = recognize_plate(image_path)

        if not result["valid"]:
            detection = save_failed_detection(
                image_path=image_path,
                plate_text=result.get("plate_text", ""),
                note=result["message"]
            )

            return jsonify({
                "allow": False,
                "action": "exit",
                "message": result["message"],
                "plate_text": result.get("plate_text", ""),
                "image_url": detection["image_url"]
            })

        plate_text = result["plate_text"]

        vehicle = find_vehicle_inside(plate_text)

        if vehicle is None:
            detection = save_failed_detection(
                image_path=image_path,
                plate_text=plate_text,
                note="Khong tim thay xe trong database"
            )

            return jsonify({
                "allow": False,
                "action": "exit",
                "plate_text": plate_text,
                "message": "Khong tim thay xe trong database",
                "image_url": detection["image_url"]
            })

        session, detection = save_vehicle_out(
            plate_text=plate_text,
            image_path=image_path,
            confidence=result.get("ocr_conf", 0)
        )

        return jsonify({
            "allow": True,
            "action": "exit",
            "plate_text": plate_text,
            "message": "Cho xe ra",
            "image_url": detection["image_url"],
            "detection_id": detection["id"],
            "parking_session_id": session["id"]
        })

    except Exception as e:
        print("[ERROR]", str(e))
        return jsonify({
            "allow": False,
            "action": "exit",
            "message": str(e)
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

    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    start_server()