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
    pinMode(DONE_PIN, OUTPUT);
    digitalWrite(DONE_PIN, HIGH); // Signal stays high when idle

    arm.attach(ARM_PIN);
    claw.attach(CLAW_PIN);

    arm.write(ARM_UP);
    claw.write(CLAW_OPEN);
}

void loop()
{
    // Listen for NodeMCU pulling the trigger LOW
    if (digitalRead(TRIGGER_PIN) == LOW)
    {
        delay(100); // Debounce

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

        // Send feedback: Pull DONE_PIN LOW
        digitalWrite(DONE_PIN, LOW);
        delay(1000);
        digitalWrite(DONE_PIN, HIGH);
    }
}

void pickup()
{
    claw.write(CLAW_OPEN);
    delay(1000);
    arm.write(ARM_DOWN);
    delay(1500);
    claw.write(CLAW_CLOSE);
    delay(1500);
    arm.write(ARM_UP);
    delay(1000);
}

void drop()
{
    arm.write(ARM_DOWN);
    delay(1500);
    claw.write(CLAW_OPEN);
    delay(1500);
    arm.write(ARM_UP);
    delay(1000);
}