import cv2
import easyocr
import re

class PlateOCR:
    def __init__(self):
        self.reader = easyocr.Reader(['en'], gpu=False)

    def preprocess_plate(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Không đọc được ảnh: {image_path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def clean_text(self, text):
        text = text.upper()
        text = re.sub(r'[^A-Z0-9.-]', '', text)
        return text

    def normalize_plate_text(self, text):
        text = text.upper().strip()
        text = re.sub(r'[^A-Z0-9.-]', '', text)

        if len(text) >= 1:
            mapping_first = {
                'G': '4',
                'S': '5',
                'O': '0',
                'I': '1',
                'Z': '2',
                'B': '8'
            }
            if text[0] in mapping_first:
                text = mapping_first[text[0]] + text[1:]

        if len(text) >= 2:
            mapping_second = {
                'O': '0',
                'I': '1',
                'Z': '2',
                'B': '8'
            }
            if text[1] in mapping_second:
                text = text[0] + mapping_second[text[1]] + text[2:]

        return text
    def format_vietnam_plate(self, text):
        text = text.replace(" ", "").upper()
        text = re.sub(r'[^A-Z0-9.]', '', text)

        # 43F003.81 → 43F-003.81
        match = re.match(r'^(\d{2}[A-Z])(\d{3}\.\d{2})$', text)
        if match:
            return f"{match.group(1)}-{match.group(2)}"

        # 43F00381 → 43F-003.81
        match = re.match(r'^(\d{2}[A-Z])(\d{5})$', text)
        if match:
            d = match.group(2)
            return f"{match.group(1)}-{d[:3]}.{d[3:]}"

        return text
    def read_plate(self, image_path):
        processed = self.preprocess_plate(image_path)
        results = self.reader.readtext(processed, detail=1)

        if not results:
            return "", 0.0

        # Lấy (text, y_center)
        items = []
        for item in results:
            bbox, raw_text, conf = item
            text = self.normalize_plate_text(self.clean_text(raw_text))

            if not text:
                continue

            y_center = sum([p[1] for p in bbox]) / 4.0
            items.append((y_center, text, float(conf)))

        if not items:
            return "", 0.0

        # sort theo chiều dọc (trên → dưới)
        items.sort(key=lambda x: x[0])

        # tách dòng
        lines = []
        current_line = [items[0]]

        for item in items[1:]:
            if abs(item[0] - current_line[-1][0]) < 25:
                current_line.append(item)
            else:
                lines.append(current_line)
                current_line = [item]
        lines.append(current_line)

        # ghép từng dòng
        merged_lines = []
        confs = []

        for line in lines:
            line_text = "".join([x[1] for x in line])
            merged_lines.append(line_text)
            confs.extend([x[2] for x in line])

        # xử lý 2 dòng
        if len(merged_lines) >= 2:
            # dòng trên + dòng dưới
            final_text = merged_lines[0] + merged_lines[1]
        else:
            final_text = merged_lines[0]

        final_text = self.format_vietnam_plate(final_text)
        avg_conf = sum(confs) / len(confs)

        return final_text, avg_conf