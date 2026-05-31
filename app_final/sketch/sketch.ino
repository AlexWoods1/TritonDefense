#include <Arduino_RouterBridge.h>

// Codes measured for this remote. Update these after running rc_map if needed.
const unsigned long IR_CODE_FORWARD = 0xB78UL;
const unsigned long IR_CODE_FORWARD2 = 0x378UL;
const unsigned long IR_CODE_BACKWARD = 0xE38UL;
const unsigned long IR_CODE_BACKWARD2 = 0x638UL;
const unsigned long IR_CODE_LEFT = 0xB38UL;
const unsigned long IR_CODE_LEFT2 = 0x338UL;
const unsigned long IR_CODE_RIGHT = 0xA38UL;
const unsigned long IR_CODE_RIGHT2 = 0x238UL;

// Toggles person-tracking on the MPU. This remote flips a toggle bit (bit 11)
// between consecutive presses, so the same button alternates between these two
// codes. Accept both so every press registers.
const unsigned long IR_CODE_TOGGLE_TRACK = 0xF78UL;
const unsigned long IR_CODE_TOGGLE_TRACK2 = 0x778UL;

// ELEGOO Smart Robot Car V4 TB6612 motor pins.
const int MOTOR_RIGHT_PWM_PIN = 5;  // PWMA, group A, right motors
const int MOTOR_LEFT_PWM_PIN = 6;   // PWMB, group B, left motors
const int MOTOR_RIGHT_DIR_PIN = 7;  // AIN1
const int MOTOR_LEFT_DIR_PIN = 8;   // BIN1
const int MOTOR_STANDBY_PIN = 3;    // STBY

const int IR_RECEIVE_PIN = 9;       // ELEGOO RECV_PIN
const int SERVO_PIN = 10;           // ELEGOO z-axis servo pin

const int MOTION_STOP = 0;
const int MOTION_FORWARD = 1;
const int MOTION_BACKWARD = 2;
const int MOTION_LEFT = 3;
const int MOTION_RIGHT = 4;
const int MOTION_CUSTOM_OUTPUTS = 5;

const int MOTOR_STOP = 0;
const int MOTOR_FORWARD = 1;
const int MOTOR_BACKWARD = -1;
const int DEFAULT_MOTOR_SPEED = 200;
const int IR_MAX_BITS = 32;
const unsigned long IR_START_LOW_MIN_US = 8000UL;
const unsigned long IR_START_LOW_MAX_US = 10000UL;
const unsigned long IR_BIT_LOW_MIN_US = 350UL;
const unsigned long IR_BIT_LOW_MAX_US = 900UL;
const unsigned long IR_ZERO_HIGH_MIN_US = 300UL;
const unsigned long IR_ZERO_HIGH_MAX_US = 900UL;
const unsigned long IR_ONE_HIGH_MIN_US = 1200UL;
const unsigned long IR_ONE_HIGH_MAX_US = 2200UL;
const unsigned long IR_REPEAT_HIGH_MIN_US = 2000UL;
const unsigned long IR_REPEAT_HIGH_MAX_US = 2600UL;
const unsigned long IR_REPEAT_LOW_MIN_US = 400UL;
const unsigned long IR_REPEAT_LOW_MAX_US = 750UL;
const unsigned long IR_PULSE_TIMEOUT_US = 30000UL;
const int SERVO_MIN_US = 500;
const int SERVO_MAX_US = 2400;
const unsigned long SERVO_REFRESH_MS = 20;

const unsigned long COMMAND_TIMEOUT_MS = 200;
const unsigned long PYTHON_TIMEOUT_MS = 20;
const bool DEBUG_LOGGING = true;

int currentMotion = MOTION_STOP;
int lastIrMotion = MOTION_STOP;
int servoAngle = 90;
bool trackingEnabled = false;
unsigned long lastServoPulseMs = 0;
unsigned long lastCommandMs = 0;
unsigned long lastPythonCommandMs = 0;

void configureMotorPins();
void refreshServo();
const char *motionName(int motion);
const char *directionName(int direction);
void printHexValue(unsigned long value);
void logMotorGroups(int leftDirection, int rightDirection, int speed);
void logMotion(int motion);
void writeMotorGroups(int leftDirection, int rightDirection, int speed);
void applyMotion(int motion);
int setMotion(int motion);
int setMotorGroups(int leftDirection, int rightDirection, int speed);
int setMotorOutputs(int motor1, int motor2, int motor3, int motor4);
int setServoAngle(int angle);
int stopMotors();
int stopFromPython();
bool codeMatches(unsigned long received, unsigned long expected);
bool inRange(unsigned long value, unsigned long low, unsigned long high);
bool readIrSignature(unsigned long *signature12, int *bitCount, bool *isRepeat);
int motionForIrCode(unsigned long signature12);
bool isTrackingToggleCode(unsigned long signature12);
void handleIrInput();

void setup() {
  configureMotorPins();

  Bridge.begin();
  Monitor.begin();

  pinMode(SERVO_PIN, OUTPUT);
  refreshServo();

  stopMotors();

  Bridge.provide("set_motion", setMotion);
  Bridge.provide("set_motor_groups", setMotorGroups);
  Bridge.provide("set_motor_outputs", setMotorOutputs);
  Bridge.provide("set_servo", setServoAngle);
  Bridge.provide("stop", stopFromPython);

  pinMode(IR_RECEIVE_PIN, INPUT);

  Monitor.println("killerbot sketch ready");
  Monitor.print("IR receiver pin D");
  Monitor.println(IR_RECEIVE_PIN);
}

void loop() {
  handleIrInput();
  refreshServo();

    // stops motors if 300ms passed between last input
  if (currentMotion != MOTION_STOP && millis() - lastCommandMs > COMMAND_TIMEOUT_MS) {
    stopMotors();
  }

  delay(10);
}

void configureMotorPins() {
  pinMode(MOTOR_RIGHT_PWM_PIN, OUTPUT);
  pinMode(MOTOR_LEFT_PWM_PIN, OUTPUT);
  pinMode(MOTOR_RIGHT_DIR_PIN, OUTPUT);
  pinMode(MOTOR_LEFT_DIR_PIN, OUTPUT);
  pinMode(MOTOR_STANDBY_PIN, OUTPUT);
}

void refreshServo() {
  if (millis() - lastServoPulseMs < SERVO_REFRESH_MS) {
    return;
  }

  int pulseWidthUs = map(servoAngle, 0, 180, SERVO_MIN_US, SERVO_MAX_US);
  digitalWrite(SERVO_PIN, HIGH);
  delayMicroseconds(pulseWidthUs);
  digitalWrite(SERVO_PIN, LOW);
  lastServoPulseMs = millis();
}

const char *motionName(int motion) {
  if (motion == MOTION_FORWARD) {
    return "forward";
  }
  if (motion == MOTION_BACKWARD) {
    return "backward";
  }
  if (motion == MOTION_LEFT) {
    return "left";
  }
  if (motion == MOTION_RIGHT) {
    return "right";
  }
  if (motion == MOTION_CUSTOM_OUTPUTS) {
    return "custom";
  }
  return "stop";
}

const char *directionName(int direction) {
  if (direction > 0) {
    return "forward";
  }
  if (direction < 0) {
    return "backward";
  }
  return "stop";
}

void printHexValue(unsigned long value) {
  Monitor.print("0x");
  Monitor.print(value, HEX);
}

void logMotorGroups(int leftDirection, int rightDirection, int speed) {
  if (!DEBUG_LOGGING) {
    return;
  }

  Monitor.print("motor outputs: STBY D");
  Monitor.print(MOTOR_STANDBY_PIN);
  Monitor.print("=");
  Monitor.print(leftDirection == MOTOR_STOP && rightDirection == MOTOR_STOP ? "LOW" : "HIGH");

  Monitor.print(" left group PWM D");
  Monitor.print(MOTOR_LEFT_PWM_PIN);
  Monitor.print(" speed=");
  Monitor.print(leftDirection == MOTOR_STOP ? 0 : speed);
  Monitor.print(" DIR D");
  Monitor.print(MOTOR_LEFT_DIR_PIN);
  Monitor.print("=");
  Monitor.print(leftDirection == MOTOR_FORWARD ? "HIGH" : "LOW");
  Monitor.print(" motion=");
  Monitor.print(directionName(leftDirection));

  Monitor.print(" right group PWM D");
  Monitor.print(MOTOR_RIGHT_PWM_PIN);
  Monitor.print(" speed=");
  Monitor.print(rightDirection == MOTOR_STOP ? 0 : speed);
  Monitor.print(" DIR D");
  Monitor.print(MOTOR_RIGHT_DIR_PIN);
  Monitor.print("=");
  Monitor.print(rightDirection == MOTOR_FORWARD ? "HIGH" : "LOW");
  Monitor.print(" motion=");
  Monitor.println(directionName(rightDirection));
}

void logMotion(int motion) {
  if (!DEBUG_LOGGING) {
    return;
  }

  Monitor.print("apply motion: ");
  Monitor.println(motionName(motion));
}

void writeMotorGroups(int leftDirection, int rightDirection, int speed) {
  leftDirection = constrain(leftDirection, -1, 1);
  rightDirection = constrain(rightDirection, -1, 1);
  speed = constrain(speed, 0, 255);

  logMotorGroups(leftDirection, rightDirection, speed);

  if (leftDirection == MOTOR_STOP && rightDirection == MOTOR_STOP) {
    digitalWrite(MOTOR_STANDBY_PIN, LOW);
    analogWrite(MOTOR_LEFT_PWM_PIN, 0);
    analogWrite(MOTOR_RIGHT_PWM_PIN, 0);
    return;
  }

  digitalWrite(MOTOR_STANDBY_PIN, HIGH);

  digitalWrite(MOTOR_LEFT_DIR_PIN, leftDirection == MOTOR_FORWARD ? HIGH : LOW);
  analogWrite(MOTOR_LEFT_PWM_PIN, leftDirection == MOTOR_STOP ? 0 : speed);

  digitalWrite(MOTOR_RIGHT_DIR_PIN, rightDirection == MOTOR_FORWARD ? HIGH : LOW);
  analogWrite(MOTOR_RIGHT_PWM_PIN, rightDirection == MOTOR_STOP ? 0 : speed);
}

void applyMotion(int motion) {
  currentMotion = motion;
  lastCommandMs = millis();
  logMotion(motion);

  if (motion == MOTION_FORWARD) {
    writeMotorGroups(MOTOR_FORWARD, MOTOR_FORWARD, DEFAULT_MOTOR_SPEED);
  } else if (motion == MOTION_BACKWARD) {
    writeMotorGroups(MOTOR_BACKWARD, MOTOR_BACKWARD, DEFAULT_MOTOR_SPEED);
  } else if (motion == MOTION_LEFT) {
    writeMotorGroups(MOTOR_BACKWARD, MOTOR_FORWARD, DEFAULT_MOTOR_SPEED);
  } else if (motion == MOTION_RIGHT) {
    writeMotorGroups(MOTOR_FORWARD, MOTOR_BACKWARD, DEFAULT_MOTOR_SPEED);
  } else {
    stopMotors();
  }
}

int setMotion(int motion) {
  if (DEBUG_LOGGING) {
    Monitor.print("python command: set_motion ");
    Monitor.println(motionName(motion));
  }
  applyMotion(motion);
  lastPythonCommandMs = millis();
  return currentMotion;
}

int setMotorGroups(int leftDirection, int rightDirection, int speed) {
  if (DEBUG_LOGGING) {
    Monitor.println("python command: set_motor_groups");
  }
  writeMotorGroups(leftDirection, rightDirection, speed);
  currentMotion = MOTION_CUSTOM_OUTPUTS;
  lastCommandMs = millis();
  lastPythonCommandMs = millis();
  return 1;
}

int setMotorOutputs(int motor1, int motor2, int motor3, int motor4) {
  if (DEBUG_LOGGING) {
    Monitor.print("python command: set_motor_outputs m1=");
    Monitor.print(motor1);
    Monitor.print(" m2=");
    Monitor.print(motor2);
    Monitor.print(" m3=");
    Monitor.print(motor3);
    Monitor.print(" m4=");
    Monitor.println(motor4);
  }

  int leftDirection = constrain(motor1 + motor3, -1, 1);
  int rightDirection = constrain(motor2 + motor4, -1, 1);

  return setMotorGroups(leftDirection, rightDirection, DEFAULT_MOTOR_SPEED);
}

int setServoAngle(int angle) {
  servoAngle = constrain(angle, 0, 180);
  refreshServo();
  lastPythonCommandMs = millis();
  if (DEBUG_LOGGING) {
    Monitor.print("python command: set_servo angle=");
    Monitor.print(servoAngle);
    Monitor.print(" pin D");
    Monitor.println(SERVO_PIN);
  }
  return servoAngle;
}

int stopMotors() {
  writeMotorGroups(MOTOR_STOP, MOTOR_STOP, 0);
  currentMotion = MOTION_STOP;
  return 1;
}

int stopFromPython() {
  if (DEBUG_LOGGING) {
    Monitor.println("python command: stop");
  }
  int result = stopMotors();
  lastPythonCommandMs = millis();
  return result;
}

bool codeMatches(unsigned long received, unsigned long expected) {
  if (expected == 0) {
    return false;
  }
  return received == expected || (received & 0xFFFUL) == expected;
}

bool inRange(unsigned long value, unsigned long low, unsigned long high) {
  return value >= low && value <= high;
}

bool readIrSignature(unsigned long *signature12, int *bitCount, bool *isRepeat) {
  *signature12 = 0;
  *bitCount = 0;
  *isRepeat = false;
  unsigned long raw = 0;

  unsigned long startLow = pulseIn(IR_RECEIVE_PIN, LOW, 100000UL);
  if (!inRange(startLow, IR_START_LOW_MIN_US, IR_START_LOW_MAX_US)) {
    return false;
  }

  unsigned long highPulse = pulseIn(IR_RECEIVE_PIN, HIGH, IR_PULSE_TIMEOUT_US);
  if (highPulse == 0) {
    return false;
  }

  // NEC repeat while held: ~9 ms LOW, ~2.25 ms HIGH, ~560 us LOW.
  if (inRange(highPulse, IR_REPEAT_HIGH_MIN_US, IR_REPEAT_HIGH_MAX_US)) {
    unsigned long repeatLow = pulseIn(IR_RECEIVE_PIN, LOW, IR_PULSE_TIMEOUT_US);
    if (inRange(repeatLow, IR_REPEAT_LOW_MIN_US, IR_REPEAT_LOW_MAX_US)) {
      *isRepeat = true;
      return true;
    }
    return false;
  }

  while (*bitCount < IR_MAX_BITS) {
    int bitValue;
    if (inRange(highPulse, IR_ZERO_HIGH_MIN_US, IR_ZERO_HIGH_MAX_US)) {
      bitValue = 0;
    } else if (inRange(highPulse, IR_ONE_HIGH_MIN_US, IR_ONE_HIGH_MAX_US)) {
      bitValue = 1;
    } else {
      break;
    }

    raw |= ((unsigned long)bitValue << *bitCount);
    *bitCount = *bitCount + 1;

    unsigned long lowPulse = pulseIn(IR_RECEIVE_PIN, LOW, IR_PULSE_TIMEOUT_US);
    if (lowPulse == 0) {
      break;
    }

    if (!inRange(lowPulse, IR_BIT_LOW_MIN_US, IR_BIT_LOW_MAX_US)) {
      break;
    }

    highPulse = pulseIn(IR_RECEIVE_PIN, HIGH, IR_PULSE_TIMEOUT_US);
    if (highPulse == 0) {
      break;
    }
  }

  if (*bitCount < 8) {
    return false;
  }
  *signature12 = raw & 0xFFFUL;
  return true;
}

bool isTrackingToggleCode(unsigned long signature12) {
  return codeMatches(signature12, IR_CODE_TOGGLE_TRACK) ||
         codeMatches(signature12, IR_CODE_TOGGLE_TRACK2);
}

int motionForIrCode(unsigned long signature12) {
  if (codeMatches(signature12, IR_CODE_FORWARD) || codeMatches(signature12, IR_CODE_FORWARD2)) {
    return MOTION_FORWARD;
  }
  else if (codeMatches(signature12, IR_CODE_BACKWARD) || codeMatches(signature12, IR_CODE_BACKWARD2)) {
    return MOTION_BACKWARD;
  }
  else if (codeMatches(signature12, IR_CODE_LEFT) || codeMatches(signature12, IR_CODE_LEFT2)) {
    return MOTION_LEFT;
  }
  else if (codeMatches(signature12, IR_CODE_RIGHT) || codeMatches(signature12, IR_CODE_RIGHT2)) {
    return MOTION_RIGHT;
  }
  return MOTION_STOP;
}

void handleIrInput() {
  unsigned long signature12 = 0;
  int bitCount = 0;
  bool isRepeat = false;
  if (!readIrSignature(&signature12, &bitCount, &isRepeat)) {
    return;
  }

  // Tracking toggle is handled before the Python-priority guard below, so it
  // works even while Python is streaming servo commands. Only act on a fresh
  // press (not held repeats) to avoid flipping the state many times per hold.
  if (!isRepeat && isTrackingToggleCode(signature12)) {
    trackingEnabled = !trackingEnabled;
    Bridge.notify("set_tracking", trackingEnabled ? 1 : 0);
    lastIrMotion = MOTION_STOP;  // don't let held repeats re-apply prior motion
    if (DEBUG_LOGGING) {
      Monitor.print("ir toggle tracking -> ");
      Monitor.println(trackingEnabled ? "ENABLED" : "DISABLED");
    }
    return;
  }

  if (millis() - lastPythonCommandMs <= PYTHON_TIMEOUT_MS) {
    if (DEBUG_LOGGING) {
      Monitor.println("ir signal ignored: recent python command has control");
    }
    return;
  }

  if (isRepeat) {
    if (lastIrMotion == MOTION_STOP) {
      return;
    }

    lastCommandMs = millis();
    if (currentMotion != lastIrMotion) {
      applyMotion(lastIrMotion);
    } else if (DEBUG_LOGGING) {
      Monitor.print("ir repeat: hold ");
      Monitor.println(motionName(lastIrMotion));
    }
    return;
  }

  int motion = motionForIrCode(signature12);
  lastIrMotion = motion;
  if (DEBUG_LOGGING) {
    Monitor.print("ir signal: bits=");
    Monitor.print(bitCount);
    Monitor.print(" signature12=");
    printHexValue(signature12);
    Monitor.print(" mapped_motion=");
    Monitor.println(motionName(motion));
  }

  applyMotion(motion);
}
