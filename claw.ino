/*
 Uno Claw & Arm Driver

 Receives a trigger signal from the NodeMCU to initiate 
 the physical payload pickup or drop sequence using 
 smooth swept servo motions.
*/

#include <Servo.h>

#define TRIGGER_PIN 2 // Wire from NodeMCU RX
#define DONE_PIN 3    // Wire to NodeMCU TX
#define ARM_PIN 9
#define CLAW_PIN 10

Servo arm;
Servo claw;

const int ARM_UP = 30;
const int ARM_DOWN = 150;
const int CLAW_OPEN = 20;
const int CLAW_CLOSE = 110;

bool objectInClaw = false;

void setup()
{
    pinMode(TRIGGER_PIN, INPUT_PULLUP);
    // Leaving DONE_PIN as INPUT (high impedance) when idle prevents short 
    // circuits if the NodeMCU uses this same wire for Serial data at boot. 
    pinMode(DONE_PIN, INPUT); 

    arm.attach(ARM_PIN);
    claw.attach(CLAW_PIN);

    arm.write(ARM_UP);
    claw.write(CLAW_OPEN);
}

void loop()
{
    // Listen for NodeMCU pulling the trigger LOW (It means: "Act Now!")
    if (digitalRead(TRIGGER_PIN) == LOW)
    {
        delay(100); // Debounce to prevent double-hits

        // State machine alternates between picking up and dropping
        if (!objectInClaw)
        {
            pickup();
            objectInClaw = true;
        }
        else
        {
            drop();
            objectInClaw = false;
        }

        // Send feedback back to NodeMCU: "I am finished moving the servos"
        // We temporarily turn it into an OUTPUT to send the LOW signal.
        pinMode(DONE_PIN, OUTPUT);
        digitalWrite(DONE_PIN, LOW);
        delay(1000);
        pinMode(DONE_PIN, INPUT); // Immediately return to Safe High-Impedance Mode
    }
}

// Servo Sweep Functions
// Rather than snapping instantly, these loops sweep the 
// servo degree-by-degree to prevent physical jerks or burnouts.

void smoothArm(int startPos, int endPos) {
    if (startPos < endPos) {
        for (int pos = startPos; pos <= endPos; pos++) {
            arm.write(pos);
            delay(15);
        }
    } else {
        for (int pos = startPos; pos >= endPos; pos--) {
            arm.write(pos);
            delay(15);
        }
    }
}

void smoothClaw(int startPos, int endPos) {
    if (startPos < endPos) {
        for (int pos = startPos; pos <= endPos; pos++) {
            claw.write(pos);
            delay(10);
        }
    } else {
        for (int pos = startPos; pos >= endPos; pos--) {
            claw.write(pos);
            delay(10);
        }
    }
}

void pickup()
{
    smoothArm(ARM_UP, ARM_DOWN);
    delay(500);
    smoothClaw(CLAW_OPEN, CLAW_CLOSE);
    delay(500);
    smoothArm(ARM_DOWN, ARM_UP);
    delay(500);
}

void drop()
{
    smoothArm(ARM_UP, ARM_DOWN);
    delay(500);
    smoothClaw(CLAW_CLOSE, CLAW_OPEN);
    delay(500);
    smoothArm(ARM_DOWN, ARM_UP);
    delay(500);
}