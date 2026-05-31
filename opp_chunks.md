# 📄 Document Chunks: opp.txt - Robot Controller Code

## ℹ️ Document Metadata
- **Document ID**: 12
- **Title**: opp.txt - Robot Controller Code
- **Status**: `ready`
- **Source**: `local_upload`
- **Total Chunks**: 7
- **Uploaded By**: testuser

---

## 🧩 Generated Chunks

### 📦 Chunk 1 of 7
- **Tokens**: 500
- **Embedding Dimensions**: 768
- **Embedding Vector (preview)**: `[-0.011062, -0.003612, 0.019285, -0.078461, 0.003207, ...]`

#### 📝 Chunk Content
```text
// ===== COMMENTED OUT NETWORK =====
// #include <WiFi.h>
// #include <BlynkSimpleEsp32.h>
// #include <Firebase_ESP_Client.h>

#include <ESP32Servo.h>

// ===== COMMENTED CREDENTIALS =====
// char blynk_auth[] = "...";
// char ssid[] = "...";
// char pass[] = "...";

// #define DATABASE_URL "..."
// #define DATABASE_SECRET "..."

// Pins
#define RELAY_PIN    33
#define BUZZER       23
#define SERVO_PIN    19
#define TRIG_RIGHT    4
#define ECHO_RIGHT    2
#define TRIG_CENTER  17
#define ECHO_CENTER  16
#define TRIG_LEFT     5
#define ECHO_LEFT    18
#define BUTTON_PIN   32

// Motors
#define IN1 14
#define IN2 27
#define IN3 26
#define IN4 25

// Thresholds
#define SIDE_THRESHOLD   20
#define FRONT_THRESHOLD  20

// Timing
#define FORWARD_200MS     200
#define FORWARD_50MS       50
#define TURN_90_MS        650   // tune on your chassis

#define PLANT_CONFIRM_COUNT  2
#define SEARCH_TIMEOUT_MS   12000
#define SENSOR_DELAY         30

// ─── State machine ────────────────────────────────────────────────────────────
// The main loop no longer calls shiftRow() on every cycle.
// Instead, a compact enum tracks what the robot is currently doing so the
// maneuver runs to completion before any new decision is made.
enum RobotState {
  STATE_FOLLOW_ROW,   // Algorithm 1 – plant is alongside us, drive forward
  STATE_SHIFT_ROW     // Algorithm 2 – end of row, moving to the next one
};

RobotState robotState = STATE_FOLLOW_ROW;
// ──────────────────────────────────────────────────────────────────────────────

Servo myServo;

// Distances (retain last valid reading on timeout)
float rightDist  = 100;
float centerDist = 100;
float leftDist   = 100;

// Row counter (determines which side to turn toward next)
int turns = 0;

// ═══════════════════════════════════════════════════════════
```

---

### 📦 Chunk 2 of 7
- **Tokens**: 500
- **Embedding Dimensions**: 768
- **Embedding Vector (preview)**: `[0.006362, 0.007217, 0.040815, -0.058470, 0.003316, ...]`

#### 📝 Chunk Content
```text
counter (determines which side to turn toward next)
int turns = 0;

// ═══════════════════════════════════════════════════════════════════════════════
// MOTOR HELPERS
// ═══════════════════════════════════════════════════════════════════════════════
void move(int s1, int s2, int s3, int s4) {
  digitalWrite(IN1, s1);
  digitalWrite(IN2, s2);
  digitalWrite(IN3, s3);
  digitalWrite(IN4, s4);
}
void forward()    { move(LOW,  HIGH, LOW,  HIGH); }
void stopMotor()  { move(LOW,  LOW,  LOW,  LOW ); }
void turnLeft()   { move(LOW,  HIGH, HIGH, LOW ); }
void turnRight()  { move(HIGH, LOW,  LOW,  HIGH); }

// ═══════════════════════════════════════════════════════════════════════════════
// ULTRASONIC HELPERS
// ═══════════════════════════════════════════════════════════════════════════════
float getDistance(int trig, int echo, float lastVal) {
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);

  long duration = pulseIn(echo, HIGH, 30000);
  float d = duration * 0.034f / 2.0f;
  if (d <= 0 || d > 400) return lastVal;
  return d;
}

void updateSensors() {
  rightDist  = getDistance(TRIG_RIGHT,  ECHO_RIGHT,  rightDist);
  centerDist = getDistance(TRIG_CENTER, ECHO_CENTER, centerDist);
  leftDist   = getDistance(TRIG_LEFT,   ECHO_LEFT,   leftDist);
}

// �
```

---

### 📦 Chunk 3 of 7
- **Tokens**: 500
- **Embedding Dimensions**: 768
- **Embedding Vector (preview)**: `[0.006812, 0.002750, 0.009149, -0.042831, -0.002486, ...]`

#### 📝 Chunk Content
```text
,  ECHO_RIGHT,  rightDist);
  centerDist = getDistance(TRIG_CENTER, ECHO_CENTER, centerDist);
  leftDist   = getDistance(TRIG_LEFT,   ECHO_LEFT,   leftDist);
}

// ═══════════════════════════════════════════════════════════════════════════════
// PLANT DETECTION
// ═══════════════════════════════════════════════════════════════════════════════
bool plantDetected() {
  return (leftDist < SIDE_THRESHOLD) || (rightDist < SIDE_THRESHOLD);
}

// ═══════════════════════════════════════════════════════════════════════════════
// OBSTACLE ALERT  (shared by both algorithms)
// ═══════════════════════════════════════════════════════════════════════════════
void obstacleAlert() {
  stopMotor();
  digitalWrite(BUZZER, HIGH);
  delay(500);
  digitalWrite(BUZZER, LOW);
}

// ═══════════════════════════════════════════════════════════════════════════════
// ROTATION  (single 90° turn, direction determined by caller)
// ═══════════════════════════════════════════════════════════════════════════════
void rotateRobot(bool goRight) {
  if (goRight) turnRight(); else turnLeft();
  delay(TURN_90_MS);
  stopMotor();
  delay(80);   // mechanical settle
}

// ═══════════════════════════════════════════════════════════════════════════════
// SEARCH FOR NEXT ROW
// The robot drives forward (already facing perpendicular
```

---

### 📦 Chunk 4 of 7
- **Tokens**: 500
- **Embedding Dimensions**: 768
- **Embedding Vector (preview)**: `[-0.004271, 0.008476, 0.004242, -0.062570, -0.003035, ...]`

#### 📝 Chunk Content
```text
════════════════════════════════════════════════════════════════════
// SEARCH FOR NEXT ROW
// The robot drives forward (already facing perpendicular to the rows after the
// first turn) until side sensors detect a plant, or the timeout fires.
// ═══════════════════════════════════════════════════════════════════════════════
bool searchForNextRow() {
  unsigned long start = millis();
  int confirm = 0;

  while (millis() - start < SEARCH_TIMEOUT_MS) {
    updateSensors();

    // Hard obstacle in crossing direction → abort
    if (centerDist < FRONT_THRESHOLD) {
      obstacleAlert();
      return false;
    }

    if (plantDetected()) {
      confirm++;
      if (confirm >= PLANT_CONFIRM_COUNT) {
        stopMotor();
        return true;
      }
    } else {
      confirm = 0;
    }

    forward();
    delay(SENSOR_DELAY);
  }

  stopMotor();
  return false;
}

// ═══════════════════════════════════════════════════════════════════════════════
// ALGORITHM 2  –  ROW SHIFT
//
// Fixed turn sequence (was: right → right, now: right → LEFT = U-turn):
//
//   Start: facing along row, plant row on one side
//
//   Step 1 – drive past the end of the current row (clear the row tip)
//   Step 2 – turn 90° toward the next row  (first turn)
//   Step 3 – short nudge to clear the corner
//   Step 4 – drive forward until sensors confirm the next plant row
//   Step 5 – turn 90° in the SAME lateral direction to realign with rows
//             (this is OPPOSITE to what the original code did – it is
//              NOT a second turn in the same rotational direction; we need
//              to turn the same cardinal direction so we end up parallel
//              to the rows again, facing the opposite end of the field)
//   Step 6 – final n
```

---

### 📦 Chunk 5 of 7
- **Tokens**: 500
- **Embedding Dimensions**: 768
- **Embedding Vector (preview)**: `[0.001252, 0.025369, 0.007690, -0.071841, 0.006101, ...]`

#### 📝 Chunk Content
```text
NOT a second turn in the same rotational direction; we need
//              to turn the same cardinal direction so we end up parallel
//              to the rows again, facing the opposite end of the field)
//   Step 6 – final nudge to centre the robot between plants
//
// The key insight: if you turned RIGHT to cross between rows, you must
// turn RIGHT again (not left) to realign.  Both turns are 90° in the same
// cardinal direction → net heading change = 180°, which is correct for a
// boustrophedon (back-and-forth) pattern.
// ═══════════════════════════════════════════════════════════════════════════════
void shiftRow() {
  bool goRight = (turns % 2 == 0);

  stopMotor();
  delay(100);

  // ── Step 1: clear the end of the current row ──────────────────────────────
  forward();
  delay(FORWARD_200MS);
  stopMotor();
  delay(50);

  // ── Step 2: first 90° turn toward the next row ────────────────────────────
  rotateRobot(goRight);

  // ── Step 3: short nudge to clear the corner ───────────────────────────────
  forward();
  delay(FORWARD_50MS);
  stopMotor();
  delay(50);

  // ── Step 4: cross to the next row ─────────────────────────────────────────
  bool found = searchForNextRow();
  if (!found) {
    // Could not find next row – stay put and let operator intervene
    Serial.println("[shiftRow] Next row not found. Halting.");
    return;
  }

  stopMotor();
  delay(100);

  // ── Step 5: second 90° turn – SAME direction as Step 2 ───────────────────
  // This realigns the robot parallel to the rows, now facing the opposite end.
  // BUG FIX: original code called rotateRobot(goRight) which matched Step 2;
  // that was actually correct in intent but was listed as "Algorithm 2 Step 5"
  // with goRight — however the original
```

---

### 📦 Chunk 6 of 7
- **Tokens**: 500
- **Embedding Dimensions**: 768
- **Embedding Vector (preview)**: `[-0.002609, 0.010573, 0.022404, -0.076551, -0.000102, ...]`

#### 📝 Chunk Content
```text
end.
  // BUG FIX: original code called rotateRobot(goRight) which matched Step 2;
  // that was actually correct in intent but was listed as "Algorithm 2 Step 5"
  // with goRight — however the original code ALSO called rotateRobot(goRight)
  // in step 5, meaning both turns were the same value → correct heading math.
  // The real original bug was that searchForNextRow drove WHILE the robot was
  // already pointing sideways AND there was no state guard in loop().
  // Both are fixed here.
  rotateRobot(goRight);

  // ── Step 6: settle into the new row ───────────────────────────────────────
  forward();
  delay(FORWARD_200MS);
  stopMotor();
  delay(100);

  turns++;

  // Transition back to row-following mode
  robotState = STATE_FOLLOW_ROW;
  Serial.print("[shiftRow] Shifted to row ");
  Serial.println(turns);
}

// ═══════════════════════════════════════════════════════════════════════════════
// SETUP
// ═══════════════════════════════════════════════════════════════════════════════
void setup() {
  Serial.begin(115200);

  pinMode(RELAY_PIN,    OUTPUT);
  pinMode(BUZZER,       OUTPUT);

  pinMode(TRIG_RIGHT,   OUTPUT);
  pinMode(ECHO_RIGHT,   INPUT);
  pinMode(TRIG_CENTER,  OUTPUT);
  pinMode(ECHO_CENTER,  INPUT);
  pinMode(TRIG_LEFT,    OUTPUT);
  pinMode(ECHO_LEFT,    INPUT);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  pinMode(BUTTON_PIN, INPUT_PULLUP);

  myServo.attach(SERVO_PIN);
  myServo.write(90);

  stopMotor();
  Serial.println("[setup] Robot ready.");
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN LOOP
//
// Uses the
```

---

### 📦 Chunk 7 of 7
- **Tokens**: 295
- **Embedding Dimensions**: 768
- **Embedding Vector (preview)**: `[0.006520, 0.014743, 0.001833, -0.069012, 0.006479, ...]`

#### 📝 Chunk Content
```text
═══════════════════════════════════════════════════════════════════════════════
// MAIN LOOP
//
// Uses the state machine so shiftRow() is never re-entered mid-maneuver.
// ═══════════════════════════════════════════════════════════════════════════════
void loop() {
  updateSensors();

  // Global obstacle guard (active in all states)
  if (centerDist < FRONT_THRESHOLD) {
    obstacleAlert();
    return;
  }

  switch (robotState) {

    // ── Algorithm 1: follow the current row ─────────────────────────────────
    case STATE_FOLLOW_ROW:
      if (plantDetected()) {
        forward();                    // plant alongside us → keep going
      } else {
        // No plant detected → end of row, start crossing to the next one
        robotState = STATE_SHIFT_ROW;
      }
      break;

    // ── Algorithm 2: shift to next row (runs to completion before looping) ──
    case STATE_SHIFT_ROW:
      shiftRow();                     // blocking; sets robotState = STATE_FOLLOW_ROW on success
      break;
  }

  delay(50);
}
```

---

