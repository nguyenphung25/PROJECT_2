# Smart Parking System

Hệ thống đỗ xe thông minh sử dụng nhận diện biển số xe (ANPR) kết hợp IoT ESP32 để quản lý bãi đỗ xe tự động.
-Link video demo: 
https://drive.google.com/file/d/1PzZm6rowP1W4J40Fr4z6Ry8U4pO9Lgm7/view?usp=drivesdk

## Tổng quan

Hệ thống bao gồm 3 thành phần chính:

| Thành phần | Công nghệ | Chức năng |
|---|---|---|
| **Hardware** | ESP32 + Cảm biến IR + Servo + LCD | Điều khiển barrier cổng vào/ra, hiển thị trạng thái |
| **Backend** | Python + Flask + YOLO + EasyOCR | Nhận diện biển số, xử lý xe vào/ra, quản lý database |
| **Frontend** | HTML + CSS + JavaScript | Web dashboard giám sát và điều khiển thủ công |
| **Database** | Supabase (PostgreSQL + Storage) | Lưu trữ phiên gửi xe, ảnh chụp, lịch sử |

## Cấu trúc thư mục

```
project2/                  # Backend + Frontend
├── main.py                # Flask server chính (API endpoints)
├── detect_plate.py        # Nhận diện biển số bằng YOLO
├── ocr_plate.py           # Đọc ký tự biển số bằng EasyOCR
├── db.py                  # Quản lý database Supabase
├── models/
│   └── best.pt            # Model YOLO đã train
├── index.html             # Web dashboard
├── style.css              # Giao diện
├── main.js                # Logic frontend
├── requirements.txt       # Python dependencies
├── .env                   # Biến môi trường (Supabase credentials)
└── parking.db             # Database SQLite (backup/local)

project2_demo/             # Firmware ESP32
├── platformio.ini         # Cấu hình PlatformIO
└── src/
    └── main.cpp           # Code ESP32 (state machine điều khiển cổng)
```

## Yêu cầu

### Phần cứng

- ESP32 DevKit v1
- Cảm biến hồng ngoại (IR) x 2 (cổng vào + cổng ra)
- Servo motor (điều khiển barrier)
- Màn hình LCD 16x2 (I2C, địa chỉ 0x27)
- LED xanh, đỏ, trắng
- Webcam USB (laptop/máy tính)

### Phần mềm

**Backend:**
- Python 3.10+
- Libraries trong `requirements.txt`:
  - Flask, Flask-CORS
  - OpenCV (`opencv-python`)
  - Ultralytics (YOLO)
  - EasyOCR
  - Supabase Python SDK
  - python-dotenv

**ESP32:**
- PlatformIO
- Thư viện: `LiquidCrystal_I2C`, `ESP32Servo`

## Cài đặt

### 1. Backend

```bash
cd project2

# Tạo virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows

# Cài dependencies
pip install -r requirements.txt
```

### 2. Cấu hình environment

Tạo file `.env` trong thư mục `project2/`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_BUCKET=parking-images
```

### 3. Database (Supabase)

Chạy file `supabase_setup.sql` trên Supabase SQL Editor để tạo bảng:

```sql
-- parking_sessions: lưu phiên gửi xe
-- detections: lưu lịch sử nhận diện
```

### 4. ESP32

Sửa thông tin WiFi và IP server trong `project2_demo/src/main.cpp`:

```cpp
const char* ssid = "YOUR_WIFI";
const char* password = "YOUR_PASSWORD";
const char* entryServer = "http://YOUR_IP:5000/entry";
const char* exitServer  = "http://YOUR_IP:5000/exit";
```

Flash firmware bằng PlatformIO:

```bash
cd project2_demo
pio run -t upload
```

### 5. Chạy hệ thống

```bash
# Terminal 1 - Flask server
cd project2
python main.py

# Terminal 2 - Mở browser
# Truy cập http://localhost:5000
```

## Sơ đồ kết nối phần cứng

```
ESP32
├── GPIO 18 ──── IR Sensor cổng vào (INPUT)
├── GPIO 19 ──── IR Sensor cổng ra (INPUT)
├── GPIO 25 ──── Servo Motor barrier (PWM)
├── GPIO 26 ──── LED Xanh (OUTPUT)
├── GPIO 27 ──── LED Đỏ (OUTPUT)
├── GPIO 32 ──── LED Trắng (OUTPUT)
├── GPIO 21 ──── I2C SDA → LCD
└── GPIO 22 ──── I2C SCL → LCD
```

## API Endpoints

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/entry` | Xử lý xe vào (chụp ảnh, nhận diện, mở barrier) |
| GET | `/exit` | Xử lý xe ra (chụp ảnh, nhận diện, mở barrier) |
| GET | `/state/latest` | Lấy trạng thái mới nhất (entry/exit) |
| POST | `/state/reset` | Reset trạng thái hệ thống |
| GET | `/esp32/sync` | Đồng bộ số xe cho ESP32 |
| GET | `/esp32/check-reset` | ESP32 poll lệnh reset từ web |
| GET | `/esp32/vehicle-passed` | Xác nhận xe đã đi qua IR sensor |
| GET | `/sessions/latest` | Phiên gửi xe gần nhất (24h) |
| GET | `/sessions/24h` | Tất cả phiên trong 24h |
| GET | `/video_feed` | Stream video từ webcam |
| POST | `/manual/confirm` | Nhập biển số thủ công |

## Quy trình hoạt động

### Xe vào

1. Cảm biến IR cổng vào phát hiện xe → ESP32 gửi request `/entry`
2. Flask server chụp ảnh từ webcam → YOLO nhận diện vùng biển số
3. EasyOCR đọc ký tự trên biển số
4. Kiểm tra định dạng biển số Việt Nam (2 số + 1 chữ + 5 số)
5. Nếu hợp lệ → lưu vào Supabase → mở barrier servo
6. Xe đi qua IR cổng ra → ESP32 đóng barrier, cập nhật LCD

### Xe ra

1. Cảm biến IR cổng ra phát hiện xe → ESP32 gửi request `/exit`
2. Chụp ảnh, nhận diện biển số
3. Tìm kiếm trong database (status = "inside")
4. Nếu tìm thấy → cập nhật exit_time → mở barrier
5. Xe đi qua IR cổng vào → ESP32 đóng barrier

### Xử lý lỗi

- **Biển số không nhận diện được**: Web UI hiển thị panel nhập thủ công
- **Xe không có trong database**: Từ chối mở barrier, hiển thị lỗi 3s
- **Bãi đầy**: Hiển thị "Parking FULL!" trên LCD, không mở barrier
- **Timeout 10s**: Tự động đóng barrier an toàn nếu xe không đi qua

## Chức năng đặc biệt

- **Non-blocking request**: ESP32 sử dụng state machine thay vì `delay()` để hệ thống luôn responsive
- **Đồng bộ real-time**: ESP32 poll server mỗi 3 giây để cập nhật LCD khi có thay đổi từ Web UI
- **Reset từ Web UI**: Admin có thể reset hệ thống qua web, ESP32 tự nhận lệnh và về trạng thái IDLE
- **Nhận diện đa biển số**: YOLO có thể phát hiện nhiều biển số trong một ảnh
- **Chống nhận diện sai**: Flag `vehicleJustEntered` / `vehicleJustExited` tránh trigger nhầm khi xe đang đi qua cảm biến

## Credits

- Eliyas Science Info - IoT Smart Parking System (nguồn tham khảo ban đầu)
- Ultralytics YOLO
- EasyOCR
- Supabase
