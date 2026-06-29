// Nguồn tham khảo gốc:
// Eliyas Science Info - IoT Smart Parking System

// ====================== KHAI BÁO THƯ VIỆN ======================
#include <Arduino.h>
// WiFi.h: dùng để kết nối ESP32 với mạng WiFi.
#include <WiFi.h>

// HTTPClient.h: dùng để gửi request HTTP từ ESP32 lên server.
// Trong code này ESP32 gửi GET request tới server để kiểm tra biển số xe.
#include <HTTPClient.h>

// Wire.h: thư viện giao tiếp I2C, cần cho màn hình LCD I2C.
#include <Wire.h>

// LiquidCrystal_I2C.h: điều khiển LCD 16x2 thông qua giao tiếp I2C.
#include <LiquidCrystal_I2C.h>

// ESP32Servo.h: điều khiển servo bằng ESP32.
// Servo được dùng làm thanh chắn/barrier của bãi xe.
#include <ESP32Servo.h>

// ====================== KHAI BÁO LCD ======================
// Tạo đối tượng LCD I2C.
// 0x27 là địa chỉ I2C thường gặp của LCD.
// 16, 2 nghĩa là LCD có 16 cột và 2 dòng.
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ====================== KHAI BÁO CHÂN PHẦN CỨNG ======================
// Cảm biến hồng ngoại ở cổng vào.
#define IR_ENTRY 18

// Cảm biến hồng ngoại ở cổng ra.
#define IR_EXIT 19

// Chân điều khiển servo đóng/mở cổng.
#define SERVO_PIN 25

// LED xanh: báo còn chỗ trống hoặc trạng thái bình thường.
#define GREEN_LED 26

// LED đỏ: báo bãi đầy, đang quét biển số, hoặc xe không hợp lệ.
#define RED_LED 27

// Tạo đối tượng servo để điều khiển barrier.
Servo barrierServo;

// ====================== THÔNG TIN WIFI ======================
// Tên WiFi ESP32 sẽ kết nối.
const char* ssid = "Mai Yeu FPT 2.4";

// Mật khẩu WiFi.
const char* password = "maiyeufpt210hehe";

// ====================== ĐỊA CHỈ SERVER ======================
// API xử lý xe vào.
// Khi có xe vào, ESP32 gửi request tới địa chỉ này.
const char* entryServer = "http://192.168.1.9:5000/entry";

// API xử lý xe ra.
// Khi có xe ra, ESP32 gửi request tới địa chỉ này.
const char* exitServer  = "http://192.168.1.9:5000/exit";

// ====================== BIẾN TRẠNG THÁI HỆ THỐNG ======================
// Tổng số chỗ trong bãi xe.
int totalSlots = 4;

// Số chỗ còn trống hiện tại.
// Ban đầu bãi xe trống nên availableSlots = totalSlots = 4.
int availableSlots = 4;

// Trạng thái cổng hiện tại, dùng để hiển thị lên LCD.
String gateStatus = "Closed";

const int GATE_OPEN_ANGLE = 90;
const int GATE_CLOSE_ANGLE = 0;

// ====================== BIẾN CHO GỬI REQUEST NON-BLOCKING ======================
HTTPClient asyncHttpClient;   // HTTPClient duy nhất dùng cho async request
bool lastRequestAllow = false; // Ket qua allow tu server (true/false)
bool requestActive = false;    // Dang co request dang gui khong

// ====================== BIẾN CHO ĐỒNG BỘ LCD ======================
unsigned long lastSyncTime = 0;        // Thoi gian lan cuoi dong bo voi server
const unsigned long SYNC_INTERVAL = 3000;  // Dong bo moi 3 giây

// ====================== STATE MACHINE ======================
// Các trạng thái của hệ thống.
enum SystemState {
  IDLE,                       // Chờ phát hiện xe
  ENTRY_SCANNING,             // Đang quét biển số xe vào
  ENTRY_SENDING,              // Gui request server (non-blocking)
  ENTRY_WAITING_RESPONSE,     // Dap pha response tu server
  ENTRY_BARRIER_OPEN,         // Barrier đang mở cho xe vào
  ENTRY_BARRIER_CLOSE_WAIT,   // Đợi đóng barrier sau khi xe vào
  ENTRY_ERROR,                // Biển số không hợp lệ
  EXIT_SCANNING,              // Đang quét biển số xe ra
  EXIT_SENDING,               // Gui request server (non-blocking)
  EXIT_WAITING_RESPONSE,      // Dap pha response tu server
  EXIT_BARRIER_OPEN,          // Barrier đang mở cho xe ra
  EXIT_BARRIER_CLOSE_WAIT,    // Đợi đóng barrier sau khi xe ra
  EXIT_ERROR,                 // Xe không có trong database
  FULL_DISPLAY                // Hiển thị bãi đầy
};

// Trạng thái hiện tại của hệ thống.
SystemState currentState = IDLE;

// Thời gian bắt đầu state hiện tại (dùng millis() thay delay()).
unsigned long stateStartTime = 0;

// ====================== BIẾN CHỐNG NHẬN DIỆN SAI ======================
// Đánh dấu xe vừa mới vào bãi.
// Khi true, IR_EXIT sẽ bị bỏ qua để tránh nhận diện nhầm.
bool vehicleJustEntered = false;

// Đánh marca xe vừa mới ra khỏi bãi.
// Khi true, IR_ENTRY sẽ bị bỏ qua để tránh nhận diện nhầm.
bool vehicleJustExited = false;

// Gui tin hieu reset den server khi xe di qua IR sensor.
// Dam bao chi gui 1 lan cho moi lan xe di qua.
bool resetSentAfterPass = false;

// ====================== HÀM CẬP NHẬT LCD VÀ LED ======================
void updateLCD() {
  // Số xe đang đỗ = tổng số chỗ - số chỗ còn trống.
  int occupiedSlots = totalSlots - availableSlots;

  // Xóa toàn bộ nội dung cũ trên LCD trước khi in nội dung mới.
  lcd.clear();

  // Dòng 1: hiển thị số xe đang đỗ / tổng số chỗ.
  // Ví dụ: Cars:2/4
  lcd.setCursor(0, 0);
  lcd.print("Cars:");
  lcd.print(occupiedSlots);
  lcd.print("/");
  lcd.print(totalSlots);

  // Dòng 2: hiển thị số chỗ trống và trạng thái cổng.
  // Ví dụ: Free:2 Gate:Closed
  lcd.setCursor(0, 1);
  lcd.print("Free:");
  lcd.print(availableSlots);
  lcd.print(" Gate:");
  lcd.print(gateStatus);

  // Nếu vẫn còn chỗ trống thì bật LED xanh, tắt LED đỏ.
  if (availableSlots > 0) {
    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(RED_LED, LOW);
  }
  // Nếu hết chỗ thì bật LED đỏ, tắt LED xanh.
  else {
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED, HIGH);
  }
}

// ====================== HÀM GỬI REQUEST LÊN SERVER ======================
bool sendRequestToServer(const char* url) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected");
    return false;
  }

  HTTPClient http;

  Serial.print("Dang gui request den: ");
  Serial.println(url);

  http.begin(url);
  http.setTimeout(45000);

  int httpCode = http.GET();

  Serial.print("HTTP code: ");
  Serial.println(httpCode);

  if (httpCode <= 0) {
    Serial.print("HTTP error: ");
    Serial.println(http.errorToString(httpCode));
    http.end();
    return false;
  }

  String response = http.getString();
  http.end();

  Serial.println("===== RESPONSE GOC =====");
  Serial.println(response);

  String compact = response;
  compact.replace(" ", "");
  compact.replace("\n", "");
  compact.replace("\r", "");
  compact.replace("\t", "");

  Serial.println("===== RESPONSE COMPACT =====");
  Serial.println(compact);

  if (httpCode == 200 && compact.indexOf("\"allow\":true") >= 0) {
    Serial.println("ESP32 DOC DUOC allow TRUE");
    return true;
  }

  Serial.println("ESP32 KHONG DOC DUOC allow TRUE");
  return false;
}

// ====================== HÀM KIỂM TRA LỆNH RESET TỪ WEB UI ======================
// Khi user bấm Reset trên web, Python server sẽ set reset_flag = true.
// ESP32 poll endpoint này để nhận lệnh và reset state machine + LCD.
bool checkResetFromServer() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  HTTPClient http;
  http.begin("http://192.168.1.9:5000/esp32/check-reset");
  http.setTimeout(3000);

  int httpCode = http.GET();

  if (httpCode == 200) {
    String response = http.getString();
    http.end();

    if (response.indexOf("\"reset\":true") >= 0) {
      Serial.println("Nhan duoc lenh reset tu web UI");

      // Reset LCD về mặc định
      updateLCD();

      // Reset state machine
      currentState = IDLE;
      stateStartTime = millis();
      vehicleJustEntered = false;
      vehicleJustExited = false;

      return true;
    }

    return false;
  }

  http.end();
  return false;
}

// ====================== HÀM ĐỒNG BỘ LCD VỚI SERVER ======================
// Web UI co the xu ly xe vao/ra ma ESP32 khong biet.
// Ham nay poll server de lay vehicle count tu DB va cap nhat LCD.
void syncESP32WithServer() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin("http://192.168.1.9:5000/esp32/sync");
  http.setTimeout(3000);

  int httpCode = http.GET();

  if (httpCode == 200) {
    String response = http.getString();
    http.end();

    // Parse vehicle_count tu JSON: {"vehicles_inside": N, ...}
    int idx = response.indexOf("\"vehicles_inside\":");
    if (idx >= 0) {
      int valStart = idx + 18;  // do dai "\"vehicles_inside\":"
      int vehiclesInside = response.substring(valStart).toInt();
      int newAvailable = totalSlots - vehiclesInside;

      // Cap nhat neu khac voi gia tri hien tai
      if (newAvailable >= 0 && newAvailable <= totalSlots
          && newAvailable != availableSlots) {
        Serial.print("Sync LCD: vehicles=");
        Serial.print(vehiclesInside);
        Serial.print(" availableSlots ");
        Serial.print(availableSlots);
        Serial.print(" -> ");
        Serial.println(newAvailable);

        availableSlots = newAvailable;
        updateLCD();
      }
    }
    return;
  }

  http.end();
}

// ====================== HÀM GỬI REQUEST NON-BLOCKING ======================
// Bat dau gui HTTP GET request nhung KHONG block.
// Goi 1 lan, sau do dung checkAsyncResponse() de kiem tra ket qua.
void startAsyncRequest(const char* url) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected - skip request");
    lastRequestAllow = false;
    requestActive = false;
    return;
  }

  asyncHttpClient.begin(url);
  asyncHttpClient.setTimeout(45000);  // 45s - server can 15-30s + manual wait 25s
  asyncHttpClient.addHeader("Connection", "close");

  int httpCode = asyncHttpClient.GET();

  Serial.print("Async request started, HTTP code: ");
  Serial.println(httpCode);

  if (httpCode <= 0) {
    Serial.print("Async request failed: ");
    Serial.println(asyncHttpClient.errorToString(httpCode));
    asyncHttpClient.end();
    lastRequestAllow = false;
    requestActive = false;
    return;
  }

  // Request da gui thanh cong, bat dau cho response
  requestActive = true;
  lastRequestAllow = false;
}

// Kiem tra phan hoi tu server (non-blocking).
// Tra ve:
//   0  = dang cho, chua co phan hoi
//   1  = da nhan phan hoi, ket qua luu trong lastRequestAllow
//  -1  = loi (ket noi bi ngat, timeout)
int checkAsyncResponse() {
  if (!requestActive) return -1;

  // Timeout da du 30s, server co du thoi gian de tra loi
  // Kiem tra ket noi con song khong
  if (!asyncHttpClient.connected()) {
    // Ket noi da dong -> doc response cuoi cung
    String response = asyncHttpClient.getString();
    asyncHttpClient.end();
    requestActive = false;

    Serial.println("===== ASYNC RESPONSE =====");
    Serial.println(response);

    String compact = response;
    compact.replace(" ", "");
    compact.replace("\n", "");
    compact.replace("\r", "");
    compact.replace("\t", "");

    if (compact.indexOf("\"allow\":true") >= 0) {
      Serial.println("ESP32 DOC DUOC allow TRUE (async)");
      lastRequestAllow = true;
    } else {
      Serial.println("ESP32 KHONG DOC DUOC allow TRUE (async)");
      lastRequestAllow = false;
    }

    return 1;  // Da nhan ket qua
  }

  return 0;  // Van dang cho
}

// ====================== HÀM SETUP - CHẠY 1 LẦN KHI KHỞI ĐỘNG ======================
void setup() {
  // Khởi động Serial Monitor với baudrate 115200 để xem log debug.
  Serial.begin(115200);

  // Cấu hình cảm biến hồng ngoại là INPUT.
  pinMode(IR_ENTRY, INPUT);
  pinMode(IR_EXIT, INPUT);

  // Cấu hình LED là OUTPUT.
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);

  // Gắn servo vào chân SERVO_PIN.
  barrierServo.setPeriodHertz(50);
  barrierServo.attach(SERVO_PIN, 500, 2400);

  // Đặt servo ở góc đóng cổng.
  barrierServo.write(GATE_CLOSE_ANGLE);

  // Khởi tạo LCD.
  Wire.begin(21, 22);

  lcd.init();
  lcd.backlight();
  lcd.clear();

  // Bật đèn nền LCD và xóa nội dung cũ.
  lcd.backlight();
  lcd.clear();

  // Hiển thị thông báo khởi động hệ thống.
  lcd.setCursor(0, 0);
  lcd.print("Smart Parking");

  // Hiển thị trạng thái đang kết nối WiFi.
  lcd.setCursor(0, 1);
  lcd.print("Connecting WiFi");

  // Bắt đầu kết nối WiFi bằng ssid và password đã khai báo.
  WiFi.begin(ssid, password);

  // Vòng lặp chờ đến khi WiFi kết nối thành công.
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  // Khi kết nối WiFi thành công, in thông tin ra Serial Monitor.
  Serial.println(" Connected!");
  Serial.println(WiFi.localIP());

  // Hiển thị thông báo kết nối thành công trên LCD.
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("WiFi Connected");
  lcd.setCursor(0, 1);

  // In địa chỉ IP của ESP32 lên LCD.
  lcd.print(WiFi.localIP().toString().c_str());

  // Cập nhật màn hình và LED theo trạng thái ban đầu của bãi xe.
  updateLCD();
}

// ====================== HÀM LOOP - CHẠY LIÊN TỤC ======================
void loop() {
  // Đọc trạng thái cảm biến IR
  bool irEntryActive = (digitalRead(IR_ENTRY) == LOW);
  bool irExitActive  = (digitalRead(IR_EXIT) == LOW);

  // Tính thời gian đã trôi qua kể từ khi bắt đầu state hiện tại.
  unsigned long elapsed = millis() - stateStartTime;

  // ============================================================
  // STATE MACHINE - XỬ LÝ TỪNG TRẠNG THÁI
  // ============================================================
  switch (currentState) {

    // ===================== IDLE =====================
    // Trạng thái chờ, kiểm tra IR để bắt đầu xử lý xe vào/ra.
    case IDLE:
      // Kiểm tra lenh reset tu web UI moi loop iteration
      checkResetFromServer();

      // Dong bo LCD voi server moi 3 giay
      // De cap nhat so luong xe khi web UI xu ly xe vao/ra
      if (millis() - lastSyncTime >= SYNC_INTERVAL) {
        lastSyncTime = millis();
        syncESP32WithServer();
      }

      // --- Xử lý xe vào ---
      // Chi xu ly khi:
      // - IR_ENTRY phat hien xe (LOW)
      // - CA HAI flag deu false (khong co xe nao vua di qua)
      // - Bai con cho trong
      if (irEntryActive && !vehicleJustExited && !vehicleJustEntered && availableSlots > 0) {
        Serial.println("Phat hien xe vao");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Xe vao");
        lcd.setCursor(0, 1);
        lcd.print("Dang quet BS");
        digitalWrite(GREEN_LED, LOW);
        digitalWrite(RED_LED, HIGH);

        currentState = ENTRY_SCANNING;
        stateStartTime = millis();
      }
      // --- Xử lý xe ra ---
      // Chi xu ly khi:
      // - IR_EXIT phat hien xe (LOW)
      // - CA HAI flag deu false (khong co xe nao vua di qua)
      else if (irExitActive && !vehicleJustEntered && !vehicleJustExited) {
        Serial.println("Phat hien xe ra");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Xe ra");
        lcd.setCursor(0, 1);
        lcd.print("Dang quet BS");
        digitalWrite(GREEN_LED, LOW);
        digitalWrite(RED_LED, HIGH);

        currentState = EXIT_SCANNING;
        stateStartTime = millis();
      }
      // --- Xử lý bãi đầy ---
      else if (irEntryActive && availableSlots <= 0) {
        Serial.println("Bai xe day");
        lcd.clear();
        lcd.setCursor(2, 0);
        lcd.print("Parking FULL!");
        digitalWrite(GREEN_LED, LOW);
        digitalWrite(RED_LED, HIGH);

        currentState = FULL_DISPLAY;
        stateStartTime = millis();
      }

      // --- Reset ca 2 flag khi CA HAI IR deu khong active ---
      // Xe da di het khoangIR → cho phep nhan dien xe moi
      if (!irEntryActive && !irExitActive) {
        if (vehicleJustExited) {
          vehicleJustExited = false;
          Serial.println("Reset vehicleJustExited");
        }
        if (vehicleJustEntered) {
          vehicleJustEntered = false;
          Serial.println("Reset vehicleJustEntered");
        }
      }
      break;

    // ===================== ENTRY_SCANNING =====================
    // Đợi 1 giây để quét biển số xe vào.
    case ENTRY_SCANNING:
      if (elapsed >= 1000) {
        if (checkResetFromServer()) break;  // Neu nhan reset thi quay lai IDLE
        currentState = ENTRY_SENDING;
        stateStartTime = millis();
      }
      break;

    // ===================== ENTRY_SENDING =====================
    // Gui blocking request len server, doc ket qua ngay.
    case ENTRY_SENDING: {
      if (checkResetFromServer()) break;

      Serial.println("Dang gui request xe vao...");
      bool allowed = sendRequestToServer(entryServer);

      if (allowed) {
        Serial.println("Bien so hop le - Mo cong vao");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("BS hop le");
        lcd.setCursor(0, 1);
        lcd.print("Mo cong vao");

        barrierServo.write(GATE_OPEN_ANGLE);
        gateStatus = "Open";
        vehicleJustEntered = true;
        vehicleJustExited = true;

        currentState = ENTRY_BARRIER_OPEN;
        stateStartTime = millis();
      } else {
        Serial.println("Bien so khong hop le - Khong mo cong");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("BS khong hop le");
        lcd.setCursor(0, 1);
        lcd.print("Khong mo cong");
        digitalWrite(GREEN_LED, LOW);
        digitalWrite(RED_LED, HIGH);

        currentState = ENTRY_ERROR;
        stateStartTime = millis();
      }
      break;
    }

    // ===================== ENTRY_BARRIER_OPEN =====================
    // Barrier dang mo, doi xe di qua IR sensor.
    case ENTRY_BARRIER_OPEN:
      // Chan ca 2 huong khi barrier dang mo cho vao
      // Xe vua vao co the van dang qua IR Exit
      vehicleJustExited = true;
      vehicleJustEntered = true;

      // Xe vao da di qua IR Exit (D19) sau khi barrier mo
      if (irExitActive && elapsed >= 500) {
        if (!resetSentAfterPass) {
          // Gui tin hieu reset den server -> xoa anh tren Web UI
          sendRequestToServer("http://192.168.1.9:5000/esp32/vehicle-passed");
          resetSentAfterPass = true;
          Serial.println("Xe vao da qua IR Exit D19 - Reset Web UI");

          // Cap nhat LCD ve man hinh so xe
          updateLCD();
        }
        stateStartTime = millis();
        currentState = ENTRY_BARRIER_CLOSE_WAIT;
      }
      // Safety timeout 10s: dong barrier neu xe khong di qua IR
      else if (elapsed >= 10000) {
        if (checkResetFromServer()) break;
        if (!resetSentAfterPass) {
          sendRequestToServer("http://192.168.1.9:5000/esp32/vehicle-passed");
          resetSentAfterPass = true;
        }
        barrierServo.write(GATE_CLOSE_ANGLE);
        gateStatus = "Closed";
        vehicleJustExited = true;
        vehicleJustEntered = true;
        updateLCD();
        resetSentAfterPass = false;
        Serial.println("Safety timeout - dong barrier - xe vao");
        currentState = IDLE;
      }
      break;

    // ===================== ENTRY_BARRIER_CLOSE_WAIT =====================
    // Dong barrier va hoan tat qua trinh xe vao.
    case ENTRY_BARRIER_CLOSE_WAIT:
      if (elapsed >= 1000) {
        if (checkResetFromServer()) break;
        // Fallback: gui reset neu chua gui (IR khong trigger)
        if (!resetSentAfterPass) {
          sendRequestToServer("http://192.168.1.9:5000/esp32/vehicle-passed");
          resetSentAfterPass = true;
        }
        // Dong barrier.
        barrierServo.write(GATE_CLOSE_ANGLE);
        gateStatus = "Closed";
        if (availableSlots > 0) {
          availableSlots--;
        }
        vehicleJustExited = true;
        vehicleJustEntered = true;
        updateLCD();
        resetSentAfterPass = false;
        Serial.println("Xe vao thanh cong - quay lai IDLE");
        currentState = IDLE;
      }
      break;

    // ===================== ENTRY_ERROR =====================
    // Hiển thị lỗi 3 giây rồi quay về IDLE.
    case ENTRY_ERROR:
      if (elapsed >= 3000) {
        if (checkResetFromServer()) break;  // Neu nhan reset thi quay lai IDLE
        updateLCD();
        currentState = IDLE;
      }
      break;

    // ===================== EXIT_SCANNING =====================
    // Đợi 1 giây để quét biển số xe ra.
    case EXIT_SCANNING:
      if (elapsed >= 1000) {
        if (checkResetFromServer()) break;  // Neu nhan reset thi quay lai IDLE
        currentState = EXIT_SENDING;
        stateStartTime = millis();
      }
      break;

    // ===================== EXIT_SENDING =====================
    // Gui blocking request len server, doc ket qua ngay.
    case EXIT_SENDING: {
      if (checkResetFromServer()) break;

      Serial.println("Dang gui request xe ra...");
      bool allowed = sendRequestToServer(exitServer);

      if (allowed) {
        Serial.println("Bien so co trong database - Mo cong ra");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Xe hop le");
        lcd.setCursor(0, 1);
        lcd.print("Mo cong ra");

        barrierServo.write(GATE_OPEN_ANGLE);
        gateStatus = "Open";
        vehicleJustExited = true;
        vehicleJustEntered = true;

        currentState = EXIT_BARRIER_OPEN;
        stateStartTime = millis();
      } else {
        Serial.println("Khong tim thay xe - Khong mo cong");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Xe khong co");
        lcd.setCursor(0, 1);
        lcd.print("trong DB");
        digitalWrite(GREEN_LED, LOW);
        digitalWrite(RED_LED, HIGH);

        currentState = EXIT_ERROR;
        stateStartTime = millis();
      }
      break;
    }

    // ===================== EXIT_BARRIER_OPEN =====================
    // Barrier dang mo, doi xe di qua IR sensor.
    case EXIT_BARRIER_OPEN:
      // Chan ca 2 huong khi barrier dang mo cho ra
      // Xe vua ra co the van dang qua IR Entry
      vehicleJustEntered = true;
      vehicleJustExited = true;

      // Xe ra da di qua IR Entry (D18) sau khi barrier mo
      if (irEntryActive && elapsed >= 500) {
        if (!resetSentAfterPass) {
          // Gui tin hieu reset den server -> xoa anh tren Web UI
          sendRequestToServer("http://192.168.1.9:5000/esp32/vehicle-passed");
          resetSentAfterPass = true;
          Serial.println("Xe ra da qua IR Entry D18 - Reset Web UI");

          // Cap nhat LCD ve man hinh so xe
          updateLCD();
        }
        stateStartTime = millis();
        currentState = EXIT_BARRIER_CLOSE_WAIT;
      }
      // Safety timeout 10s: dong barrier neu xe khong di qua IR
      else if (elapsed >= 10000) {
        if (checkResetFromServer()) break;
        if (!resetSentAfterPass) {
          sendRequestToServer("http://192.168.1.9:5000/esp32/vehicle-passed");
          resetSentAfterPass = true;
        }
        barrierServo.write(GATE_CLOSE_ANGLE);
        gateStatus = "Closed";
        vehicleJustEntered = true;
        vehicleJustExited = true;
        updateLCD();
        resetSentAfterPass = false;
        Serial.println("Safety timeout - dong barrier - xe ra");
        currentState = IDLE;
      }
      break;

    // ===================== EXIT_BARRIER_CLOSE_WAIT =====================
    // Dong barrier va hoan tat qua trinh xe ra.
    case EXIT_BARRIER_CLOSE_WAIT:
      if (elapsed >= 1000) {
        if (checkResetFromServer()) break;
        // Fallback: gui reset neu chua gui (IR khong trigger)
        if (!resetSentAfterPass) {
          sendRequestToServer("http://192.168.1.9:5000/esp32/vehicle-passed");
          resetSentAfterPass = true;
        }
        // Dong barrier.
        barrierServo.write(GATE_CLOSE_ANGLE);
        gateStatus = "Closed";
        if (availableSlots < totalSlots) {
          availableSlots++;
        }
        vehicleJustEntered = true;
        vehicleJustExited = true;
        updateLCD();
        resetSentAfterPass = false;
        Serial.println("Xe ra thanh cong - quay lai IDLE");
        currentState = IDLE;
      }
      break;

    // ===================== EXIT_ERROR =====================
    // Hiển thị lỗi 3 giây rồi quay về IDLE.
    case EXIT_ERROR:
      if (elapsed >= 3000) {
        if (checkResetFromServer()) break;  // Neu nhan reset thi quay lai IDLE
        updateLCD();
        currentState = IDLE;
      }
      break;

    // ===================== FULL_DISPLAY =====================
    // Hiển thị bãi đầy 2 giây rồi quay về IDLE.
    case FULL_DISPLAY:
      if (elapsed >= 2000) {
        if (checkResetFromServer()) break;  // Neu nhan reset thi quay lai IDLE
        updateLCD();
        currentState = IDLE;
      }
      break;
  }
}
