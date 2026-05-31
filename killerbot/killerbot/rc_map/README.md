# RC Map IR Receiver Utility

Use this App Lab utility to discover which codes your IR remote sends.

## Wiring

- IR receiver `OUT` or `S` pin: D9
- IR receiver `VCC`: 3.3 V or 5 V, depending on your receiver module
- IR receiver `GND`: GND

If you use a different signal pin, update `IR_RECEIVE_PIN` in `sketch/sketch.ino`.

## App Lab Setup

Run this app, then open the App Lab Serial Monitor. Press buttons on the IR remote. The monitor prints bit count, raw pulse-decoded data, and a `signature12` value you can copy into the main car-control program.

This utility does not require the `IRremote` library. It reads the IR receiver pulses directly and prints a `signature12` value. Copy those values into the main app's `IR_CODE_*` constants.

UNO Q App Lab routes normal `Serial.print()` output to hardware UART pins, so this sketch uses `Monitor.print()` / `Monitor.println()` for terminal output.
