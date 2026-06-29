from ultralytics import YOLO
import cv2
import os
import numpy as np
from db import upload_image_bytes


class PlateDetector:
    def __init__(self, model_path="models/best.pt"):
        self.model = YOLO(model_path)

    def detect(self, image_input, conf=0.25):
        """
        Nhan dien bien so tu anh.
        image_input: duong dan file HOAC numpy array (BGR).
        """
        results = self.model.predict(source=image_input, conf=conf, save=False, verbose=False)
        return results

    def crop_plates(self, image_input, conf=0.25):
        """
        Cat bien so va upload len Supabase.
        Khong luu file local.

        Tra ve:
            crop_arrays: list numpy array (de dung cho OCR)
            crop_urls: list Supabase URL
            plate_boxes: list dict {x1, y1, x2, y2, confidence}
        """
        # Doc anh tu file hoac numpy array
        if isinstance(image_input, np.ndarray):
            image = image_input
        else:
            image = cv2.imread(image_input)
            if image is None:
                raise ValueError(f"Khong doc duoc anh: {image_input}")

        results = self.detect(image_input, conf=conf)

        crop_arrays = []
        crop_urls = []
        plate_boxes = []

        # Ten file goc de tao ten crop
        if isinstance(image_input, str):
            base_name = os.path.splitext(os.path.basename(image_input))[0]
        else:
            import time
            base_name = f"frame_{int(time.time())}"

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                score = float(box.conf[0])

                h, w = image.shape[:2]
                pad = 15
                x1 = max(0, x1 - pad)
                y1 = max(0, y1 - pad)
                x2 = min(w, x2 + pad)
                y2 = min(h, y2 + pad)

                crop = image[y1:y2, x1:x2]

                # Encode crop thanh JPEG bytes va upload truc tiep
                crop_name = f"{base_name}_plate_{i}.jpg"
                _, buffer = cv2.imencode(".jpg", crop)
                crop_url = upload_image_bytes(buffer.tobytes(), crop_name, folder="crops")

                crop_arrays.append(crop)
                crop_urls.append(crop_url)
                plate_boxes.append({
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "confidence": score
                })

        return crop_arrays, crop_urls, plate_boxes
