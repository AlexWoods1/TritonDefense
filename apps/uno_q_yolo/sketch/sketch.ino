// Minimal MCU sketch — Bridge link only. Motor control via elegoo_sentry later.
#include <Arduino_RouterBridge.h>

void setup() {
  Bridge.begin();
  Serial.println("TritonDefense YOLO MCU ready");
}

void loop() {}
