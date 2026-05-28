import os
import cv2
import time
import re

from detect_plate import PlateDetector
from ocr_plate import PlateOCR
from db import init_db, save_vehicle_in


def clean_plate_text(text):
    if text is None:
        return ""

    text = text.upper()
    text = re.sub(r"[^A-Z0-9]", "", text)

    return text


def is_valid_plate(plate_text):
    """
    Kiểm tra biển số đơn giản:
    - Không rỗng
    - Độ dài từ 6 đến 10 ký tự
    - Có cả chữ và số
    """
    if not plate_text:
        return False

    if len(plate_text) < 6 or len(plate_text) > 10:
        return False

    has_digit = any(c.isdigit() for c in plate_text)
    has_alpha = any(c.isalpha() for c in plate_text)

    return has_digit and has_alpha


def sharpen_image(frame):
    """
    Làm nét ảnh trước khi đưa vào nhận diện.
    Giúp OCR đọc biển số rõ hơn nếu webcam hơi mờ.
    """
    blurred = cv2.GaussianBlur(frame, (0, 0), 3)
    sharpened = cv2.addWeighted(frame, 1.5, blurred, -0.5, 0)

    return sharpened


def recognize_plate(image_path, detector, ocr):
    crop_paths, plate_boxes = detector.crop_plates(image_path)

    if not crop_paths:
        print("[INFO] Không phát hiện biển số")
        return None

    best_result = None

    for crop_path, box in zip(crop_paths, plate_boxes):
        plate_text, ocr_conf = ocr.read_plate(crop_path)
        plate_text = clean_plate_text(plate_text)

        print("Ảnh:", image_path)
        print("Crop:", crop_path)
        print("Biển số đọc được:", plate_text)
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
        print("[INFO] Không đọc được biển số")
        return None

    plate_text = best_result["plate_text"]

    if not is_valid_plate(plate_text):
        print(f"[INFO] Biển số không hợp lệ: {plate_text}")
        return None

    return best_result


def open_camera():
    """
    Máy có thể có nhiều camera:
    - HP HD Camera
    - HP IR Camera
    - Web Camera

    Thử lần lượt các index 1, 0, 2, 3.
    """
    camera_indexes = [1]

    for index in camera_indexes:
        print(f"[INFO] Thử mở webcam index {index}")

        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

        if cap.isOpened():
            # Ép webcam lấy độ phân giải cao hơn
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            # Tăng FPS nếu camera hỗ trợ
            cap.set(cv2.CAP_PROP_FPS, 30)

            # Bật autofocus nếu camera hỗ trợ
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)

            # Một số webcam hỗ trợ chỉnh các thông số này
            cap.set(cv2.CAP_PROP_BRIGHTNESS, 150)
            cap.set(cv2.CAP_PROP_CONTRAST, 50)
            cap.set(cv2.CAP_PROP_SHARPNESS, 100)

            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = cap.get(cv2.CAP_PROP_FPS)

            print(f"[INFO] Mở webcam thành công index {index}")
            print(f"[INFO] Độ phân giải webcam: {int(width)}x{int(height)}")
            print(f"[INFO] FPS: {fps}")

            return cap

        cap.release()

    return None


def run_webcam_capture():
    init_db()

    print("[INFO] Đang load YOLO model...")
    detector = PlateDetector("models/best.pt")

    print("[INFO] Đang load OCR model...")
    ocr = PlateOCR()

    print("[INFO] Đang mở webcam laptop...")
    cap = open_camera()

    if cap is None or not cap.isOpened():
        print("[ERROR] Không mở được webcam")
        return

    os.makedirs("test_images", exist_ok=True)

    print("[INFO] Webcam đang chạy")
    print("[INFO] Nhấn ENTER để chụp ảnh và nhận diện biển số")
    print("[INFO] Nhấn Q hoặc ESC để thoát")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("[ERROR] Không đọc được hình ảnh từ webcam")
            break

        display_frame = frame.copy()

        cv2.putText(
            display_frame,
            "ENTER: capture & recognize | Q/ESC: quit",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        cv2.imshow("License Plate Recognition - Webcam", display_frame)

        key = cv2.waitKey(1) & 0xFF

        # ENTER
        if key == 13:
            timestamp = int(time.time())
            image_path = f"test_images/capture_{timestamp}.jpg"

            # Làm nét ảnh trước khi lưu
            sharp_frame = sharpen_image(frame)

            # Lưu ảnh chất lượng cao
            cv2.imwrite(
                image_path,
                sharp_frame,
                [cv2.IMWRITE_JPEG_QUALITY, 100]
            )

            print(f"[INFO] Đã chụp ảnh: {image_path}")

            result = recognize_plate(image_path, detector, ocr)

            if result is None:
                print("[RESULT] Không nhận diện được biển số")
                print("=" * 60)
                continue

            plate_text = result["plate_text"]

            print("[RESULT] Nhận diện thành công")
            print("Biển số:", plate_text)
            print("Detect conf:", result["detect_conf"])
            print("OCR conf:", result["ocr_conf"])
            print("Crop path:", result["crop_path"])
            print("=" * 60)

            # Lưu vào database dạng xe vào
            save_vehicle_in(plate_text, image_path)

        # Q hoặc ESC
        elif key == ord("q") or key == 27:
            print("[INFO] Thoát chương trình")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_webcam_capture()