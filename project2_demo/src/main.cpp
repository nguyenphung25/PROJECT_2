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
const char* ssid = "PHUNG";

// Mật khẩu WiFi.
const char* password = "phung122";

// ====================== ĐỊA CHỈ SERVER ======================
// API xử lý xe vào.
// Khi có xe vào, ESP32 gửi request tới địa chỉ này.
const char* entryServer = "http://10.115.95.17:5000/entry";

// API xử lý xe ra.
// Khi có xe ra, ESP32 gửi request tới địa chỉ này.
const char* exitServer  = "http://10.115.95.17:5000/exit";

// ====================== BIẾN TRẠNG THÁI HỆ THỐNG ======================
// Tổng số chỗ trong bãi xe.
int totalSlots = 10;

// Số chỗ còn trống hiện tại.
// Ban đầu bãi xe trống nên availableSlots = totalSlots = 4.
int availableSlots = 10;

// Cờ chống xử lý lặp cho cảm biến cổng vào.
// Vì loop() chạy liên tục, nếu xe đứng trước cảm biến lâu thì cảm biến vẫn LOW nhiều lần.
// flagEntry giúp chỉ xử lý một lần cho mỗi lượt xe vào.
int flagEntry = 0;

// Cờ chống xử lý lặp cho cảm biến cổng ra.
int flagExit = 0;

// Trạng thái cổng hiện tại, dùng để hiển thị lên LCD.
String gateStatus = "Closed";

const int GATE_OPEN_ANGLE = 90;
const int GATE_CLOSE_ANGLE = 0;
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

// ====================== HÀM HIỂN THỊ BÃI XE ĐẦY ======================
void showFullMessage() {
  // Xóa màn hình và hiển thị thông báo bãi xe đầy.
  lcd.clear();
  lcd.setCursor(2, 0);
  lcd.print("Parking FULL!");

  // Khi bãi đầy thì bật LED đỏ, tắt LED xanh.
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, HIGH);

  // Giữ thông báo trong 2 giây.
  delay(2000);

  // Sau đó quay lại màn hình trạng thái chính.
  updateLCD();
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
  http.setTimeout(30000);

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
//Hàm mở barrier
void openBarrier() {
  Serial.println("===== BAT DAU MO BARRIER =====");

  gateStatus = "Open";

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("BARRIER OPEN");
  lcd.setCursor(0, 1);
  lcd.print("Please pass");

  barrierServo.write(GATE_OPEN_ANGLE);
  delay(5000);

  barrierServo.write(GATE_CLOSE_ANGLE);

  gateStatus = "Closed";

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("BARRIER CLOSED");
  lcd.setCursor(0, 1);
  lcd.print("Wait...");
  delay(1000);

  Serial.println("===== DA DONG BARRIER =====");
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

  // Đặt servo ở góc 90 độ, xem như trạng thái đóng cổng.
  // Tùy mô hình thực tế, góc đóng/mở có thể cần đổi lại.
  barrierServo.write(GATE_CLOSE_ANGLE);

  // Khởi tạo LCD.
  // Dòng lcd.begin(21, 22) thường dùng để chỉ SDA = 21, SCL = 22 trên ESP32.
  // Dòng lcd.begin(16, 2) khởi tạo kích thước LCD 16x2.
  // Lưu ý: tùy thư viện LiquidCrystal_I2C, có thể chỉ cần một trong hai cách khởi tạo.
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

  // ============================================================
  // XỬ LÝ XE VÀO BÃI
  // ============================================================
  // Điều kiện:
  // - digitalRead(IR_ENTRY) == LOW: cảm biến cổng vào phát hiện có xe.
  //   Nhiều module IR trả LOW khi phát hiện vật cản.
  // - flagEntry == 0: lượt xe này chưa được xử lý.
  if (digitalRead(IR_ENTRY) == LOW && flagEntry == 0) {
    // Đánh dấu đã xử lý xe ở cổng vào để tránh xử lý lặp liên tục.
    flagEntry = 1;

    // Chỉ cho xe vào nếu bãi còn chỗ trống.
    if (availableSlots > 0) {
      Serial.println("Phat hien xe vao");

      // Hiển thị trạng thái xe vào và đang quét biển số.
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Xe vao");
      lcd.setCursor(0, 1);
      lcd.print("Dang quet BS");

      // Trong lúc quét biển số, bật LED đỏ để báo đang xử lý/chưa cho qua.
      digitalWrite(GREEN_LED, LOW);
      digitalWrite(RED_LED, HIGH);

      // Chờ 1 giây giả lập thời gian quét biển số/xử lý ảnh.
      delay(1000);

      // Gửi request tới server xe vào.
      // Nếu server trả allow:true thì allowEntry = true.
      bool allowEntry = sendRequestToServer(entryServer);

      // Nếu biển số hợp lệ và server cho phép xe vào.
      if (allowEntry) {
        Serial.println("Bien so hop le - Mo cong vao");

        // Thông báo biển số hợp lệ và mở cổng.
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("BS hop le");
        lcd.setCursor(0, 1);
        lcd.print("Mo cong vao");

        // Cập nhật trạng thái cổng là mở.
        openBarrier();

        availableSlots--;

        updateLCD();
      }
      // Nếu server không cho phép xe vào.
      else {
        Serial.println("Bien so khong hop le - Khong mo cong");

        // Hiển thị thông báo biển số không hợp lệ.
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("BS khong hop le");
        lcd.setCursor(0, 1);
        lcd.print("Khong mo cong");

        // Giữ LED đỏ vì xe không được phép vào.
        digitalWrite(GREEN_LED, LOW);
        digitalWrite(RED_LED, HIGH);

        // Hiển thị thông báo trong 3 giây rồi quay lại màn hình chính.
        delay(3000);
        updateLCD();
      }
    }
    // Nếu bãi xe đã hết chỗ thì không xử lý quét biển số, chỉ báo FULL.
    else {
      showFullMessage();
    }
  }

  // Khi xe đã đi khỏi cảm biến cổng vào, cảm biến trở lại HIGH.
  // Reset flagEntry = 0 để lần sau có xe mới thì hệ thống xử lý tiếp.
  if (digitalRead(IR_ENTRY) == HIGH && flagEntry == 1) {
    flagEntry = 0;

    // Cập nhật lại LCD/LED theo trạng thái hiện tại.
    updateLCD();
  }

  // ============================================================
  // XỬ LÝ XE RA KHỎI BÃI
  // ============================================================
  // Điều kiện:
  // - digitalRead(IR_EXIT) == LOW: cảm biến cổng ra phát hiện có xe.
  // - flagExit == 0: lượt xe ra này chưa được xử lý.
  if (digitalRead(IR_EXIT) == LOW && flagExit == 0) {
    // Đánh dấu đã xử lý xe ở cổng ra để tránh xử lý lặp.
    flagExit = 1;

    Serial.println("Phat hien xe ra");

    // Hiển thị trạng thái xe ra và đang quét biển số.
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Xe ra");
    lcd.setCursor(0, 1);
    lcd.print("Dang quet BS");

    // Trong lúc quét biển số, bật LED đỏ.
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED, HIGH);

    // Chờ 1 giây giả lập thời gian quét biển số.
    delay(1000);

    // Gửi request tới server xe ra.
    // Server sẽ kiểm tra biển số có trong database hay không.
    bool allowExit = sendRequestToServer(exitServer);

    // Nếu xe có trong database và được phép ra.
    if (allowExit) {
      Serial.println("Bien so co trong database - Mo cong ra");

      // Hiển thị thông báo xe hợp lệ và mở cổng ra.
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Xe hop le");
      lcd.setCursor(0, 1);
      lcd.print("Mo cong ra");

      // Cập nhật trạng thái cổng là mở.
      openBarrier();

      if (availableSlots < totalSlots) {
        availableSlots++;
      }

      updateLCD();
    }
    // Nếu server không tìm thấy xe trong database.
    else {
      Serial.println("Khong tim thay xe - Khong mo cong");

      // Hiển thị thông báo xe không có trong database.
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Xe khong co");
      lcd.setCursor(0, 1);
      lcd.print("trong DB");

      // Xe không hợp lệ thì giữ LED đỏ, không mở cổng.
      digitalWrite(GREEN_LED, LOW);
      digitalWrite(RED_LED, HIGH);

      // Hiển thị thông báo trong 3 giây rồi quay lại màn hình chính.
      delay(3000);
      updateLCD();
    }
  }

  // Khi xe đã rời khỏi cảm biến cổng ra, reset flagExit.
  // Lần sau có xe ra mới thì hệ thống mới xử lý tiếp.
  if (digitalRead(IR_EXIT) == HIGH) {
    flagExit = 0;
  }
}
