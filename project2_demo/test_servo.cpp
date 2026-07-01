#include <Arduino.h>
#include <ESP32Servo.h>

Servo s;

void setup() {
  Serial.begin(115200);
  s.setPeriodHertz(50);
  s.attach(25, 500, 2400);
}

void loop() {
  Serial.println("Open");
  s.write(90);
  delay(2000);

  Serial.println("Close");
  s.write(0);
  delay(2000);
}