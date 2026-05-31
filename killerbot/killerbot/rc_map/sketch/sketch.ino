#include <Arduino_RouterBridge.h>

const int IR_RECEIVE_PIN = 9;

const int IR_MAX_BITS = 32;
const unsigned long IR_START_LOW_MIN_US = 8000UL;
const unsigned long IR_START_LOW_MAX_US = 10000UL;
const unsigned long IR_BIT_LOW_MIN_US = 350UL;
const unsigned long IR_BIT_LOW_MAX_US = 900UL;
const unsigned long IR_ZERO_HIGH_MIN_US = 300UL;
const unsigned long IR_ZERO_HIGH_MAX_US = 900UL;
const unsigned long IR_ONE_HIGH_MIN_US = 1200UL;
const unsigned long IR_ONE_HIGH_MAX_US = 2200UL;
const unsigned long IR_PULSE_TIMEOUT_US = 30000UL;

void printHex(unsigned long value) {
  Monitor.print("0x");
  Monitor.print(value, HEX);
}

bool inRange(unsigned long value, unsigned long low, unsigned long high) {
  return value >= low && value <= high;
}

bool readIrFrame(unsigned long *raw, unsigned long *signature12, int *bitCount) {
  *raw = 0;
  *signature12 = 0;
  *bitCount = 0;

  unsigned long startLow = pulseIn(IR_RECEIVE_PIN, LOW, 100000UL);
  if (!inRange(startLow, IR_START_LOW_MIN_US, IR_START_LOW_MAX_US)) {
    return false;
  }

  for (; *bitCount < IR_MAX_BITS; *bitCount = *bitCount + 1) {
    unsigned long highPulse = pulseIn(IR_RECEIVE_PIN, HIGH, IR_PULSE_TIMEOUT_US);
    if (highPulse == 0) {
      break;
    }

    int bitValue;
    if (inRange(highPulse, IR_ZERO_HIGH_MIN_US, IR_ZERO_HIGH_MAX_US)) {
      bitValue = 0;
    } else if (inRange(highPulse, IR_ONE_HIGH_MIN_US, IR_ONE_HIGH_MAX_US)) {
      bitValue = 1;
    } else {
      break;
    }

    *raw = *raw | ((unsigned long)bitValue << *bitCount);

    unsigned long lowPulse = pulseIn(IR_RECEIVE_PIN, LOW, IR_PULSE_TIMEOUT_US);
    if (lowPulse == 0) {
      break;
    }

    if (!inRange(lowPulse, IR_BIT_LOW_MIN_US, IR_BIT_LOW_MAX_US)) {
      break;
    }
  }

  if (*bitCount < 8) {
    return false;
  }

  *signature12 = *raw & 0xFFFUL;
  return true;
}

void setup() {
  Bridge.begin();
  Monitor.begin();
  pinMode(IR_RECEIVE_PIN, INPUT);

  Monitor.println("IR mapper ready.");
  Monitor.print("Receiver pin: D");
  Monitor.println(IR_RECEIVE_PIN);
  Monitor.println("Press buttons on the IR remote.");
  Monitor.println("Copy signature12 values into the main sketch IR_CODE_* constants.");
}

void loop() {
  unsigned long raw = 0;
  unsigned long signature12 = 0;
  int bitCount = 0;

  if (readIrFrame(&raw, &signature12, &bitCount)) {
    Monitor.print("bits=");
    Monitor.print(bitCount);
    Monitor.print(" raw=");
    printHex(raw);
    Monitor.print(" signature12=");
    printHex(signature12);
    Monitor.println();
  }

  delay(10);
}
