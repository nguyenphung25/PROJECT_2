from ultralytics import YOLO
import cv2
import os

class PlateDetector:
    def __init__(self, model_path="models/best.pt"):
        self.model = YOLO(model_path)

    def detect(self, image_path, conf=0.25):
        results = self.model.predict(source=image_path, conf=conf, save=False, verbose=False)
        return results

    def crop_plates(self, image_path, output_dir="output/crops", conf=0.25):
        os.makedirs(output_dir, exist_ok=True)

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Không đọc được ảnh: {image_path}")

        results = self.detect(image_path, conf=conf)

        crop_paths = []
        plate_boxes = []

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
                crop_name = f"{os.path.splitext(os.path.basename(image_path))[0]}_plate_{i}.jpg"
                crop_path = os.path.join(output_dir, crop_name)

                cv2.imwrite(crop_path, crop)

                crop_paths.append(crop_path)
                plate_boxes.append({
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "confidence": score
                })

        return crop_paths, plate_boxes