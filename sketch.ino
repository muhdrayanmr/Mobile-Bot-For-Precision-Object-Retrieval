/*
 NodeMCU (ESP8266) Integrated Script with Claw Support
*/

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <WiFiUdp.h>

// Pins
#define IR_L D5
#define IR_R D7
#define TRIG D6
#define ECHO D1
#define A1 D3
#define A2 D2
#define B1 D4
#define B2 D8
#define EN D0

// Arduino Uno Comm Pins
#define CLAW_TRIG 3 // RX pin (GPIO 3) -> Triggers Uno to grab
#define CLAW_DONE 1 // TX pin (GPIO 1) -> Listens for Uno to finish

// Settings
int normalSpeed = 120; 
int slowSpeed = 90;   
const int TURN_MS = 160;
const int BACK_MS = 200;

const char *ssid = "Ryan";
const char *password = "24274908";
ESP8266WebServer server(80);
WiFiUDP udp;

// State Variables
String current_nav = "stop";
bool target_visible = false;
enum SystemState { EMPTY, HOLDING, DONE };
SystemState sys_state = EMPTY;
unsigned long last_cmd_time = 0; 

void setup()
{
    pinMode(IR_L, INPUT);
    pinMode(IR_R, INPUT);
    pinMode(TRIG, OUTPUT);
    pinMode(ECHO, INPUT);
    pinMode(A1, OUTPUT);
    pinMode(A2, OUTPUT);
    pinMode(B1, OUTPUT);
    pinMode(B2, OUTPUT);
    pinMode(EN, OUTPUT);
    analogWriteRange(255);
    analogWriteFreq(1000);

    WiFi.begin(ssid, password);
    
    // Start UDP for Python Auto-Discovery
    udp.begin(4210);

    // Setup Claw Pins
    pinMode(CLAW_TRIG, OUTPUT);
    digitalWrite(CLAW_TRIG, HIGH);   
    pinMode(CLAW_DONE, INPUT_PULLUP);

    auto get_state_str = []() { return sys_state == EMPTY ? "empty" : (sys_state == HOLDING ? "holding" : "done"); };
    server.on("/forward", [get_state_str]() { current_nav = "forward"; target_visible = true; last_cmd_time = millis(); server.send(200, "text/plain", get_state_str()); });
    server.on("/left", [get_state_str]()    { current_nav = "left";    target_visible = true; last_cmd_time = millis(); server.send(200, "text/plain", get_state_str()); });
    server.on("/right", [get_state_str]()   { current_nav = "right";   target_visible = true; last_cmd_time = millis(); server.send(200, "text/plain", get_state_str()); });
    server.on("/spin", [get_state_str]()    { current_nav = "spin";    target_visible = true; last_cmd_time = millis(); server.send(200, "text/plain", get_state_str()); });
    server.on("/stop", [get_state_str]()    { current_nav = "stop";    target_visible = false; last_cmd_time = millis(); server.send(200, "text/plain", get_state_str()); });

    server.begin();
}

void loop()
{
    server.handleClient(); 
    yield();

    if (target_visible && (millis() - last_cmd_time > 1000)) {
        target_visible = false;
        current_nav = "stop";
        stopMotors();
    }

    static unsigned long last_broadcast = 0;
    if (WiFi.status() == WL_CONNECTED && millis() - last_broadcast > 2000) {
        last_broadcast = millis();
        udp.beginPacket(IPAddress(255, 255, 255, 255), 4210);
        udp.print("NITC_BOT_IP:");
        udp.print(WiFi.localIP().toString());
        udp.endPacket();
    }

    float dist = getDistance();
    int left = digitalRead(IR_L);
    int right = digitalRead(IR_R);

    if (sys_state == DONE) {
        stopMotors();
        return;
    }

    if (target_visible)
    {
        if (dist < 10 && dist > 1 && current_nav != "spin")
        {
            stopMotors();
            
            if (sys_state == EMPTY) {
                // Fire claw trigger to Uno for Pickup
                digitalWrite(CLAW_TRIG, LOW);
                delay(200);
                digitalWrite(CLAW_TRIG, HIGH);

                // Wait up to 10 seconds for Uno to pull DONE line LOW
                unsigned long wait_start = millis();
                while (digitalRead(CLAW_DONE) == HIGH && (millis() - wait_start < 10000))
                {
                    server.handleClient(); 
                    yield();               
                }
                sys_state = HOLDING;
                current_nav = "stop";
                target_visible = false; // Temporarily stop tracking to allow Python to sync
            } else if (sys_state == HOLDING) {
                // Fire claw trigger to Uno for Drop-off
                digitalWrite(CLAW_TRIG, LOW);
                delay(200);
                digitalWrite(CLAW_TRIG, HIGH);

                // Wait up to 10 seconds for Uno to pull DONE line LOW
                unsigned long wait_start = millis();
                while (digitalRead(CLAW_DONE) == HIGH && (millis() - wait_start < 10000))
                {
                    server.handleClient(); 
                    yield();               
                }
                sys_state = DONE;
                current_nav = "stop";
                target_visible = false;
            }
        }
        else
        {
            int speed = (dist < 25) ? slowSpeed : normalSpeed;
            int turnSpeed = 85; // Slower turn speed for fine alignment
            if (current_nav == "forward")  forward(speed);
            else if (current_nav == "left") softLeft(turnSpeed);
            else if (current_nav == "right") softRight(turnSpeed);
            else if (current_nav == "spin") spinRight(turnSpeed);
            else stopMotors();
        }
    }
    else
    {
        if (sys_state == HOLDING) {
            stopMotors(); // Wait safely for vision.py to send the spin sweep command
        }
        else if (dist < 15 || (left == LOW && right == LOW))
        {
            backward();
            delay(BACK_MS);
            if (left == LOW) softRight(normalSpeed);
            else softLeft(normalSpeed);
            delay(TURN_MS);
        }
        else if (left == LOW) {
            softRight(normalSpeed);
            delay(100);
        }
        else if (right == LOW) {
            softLeft(normalSpeed);
            delay(100);
        }
        else
            forward(normalSpeed);
    }
}

void forward(int spd)
{
    analogWrite(EN, spd);
    digitalWrite(A1, LOW);
    digitalWrite(A2, HIGH);
    digitalWrite(B1, LOW);
    digitalWrite(B2, HIGH);
}

void backward()
{
    analogWrite(EN, 150); 
    digitalWrite(A1, HIGH);
    digitalWrite(A2, LOW);
    digitalWrite(B1, HIGH);
    digitalWrite(B2, LOW);
}

void softRight(int spd)
{
    analogWrite(EN, spd);
    digitalWrite(A1, LOW);
    digitalWrite(A2, HIGH);
    digitalWrite(B1, LOW);
    digitalWrite(B2, LOW); 
}

void softLeft(int spd)
{
    analogWrite(EN, spd);
    digitalWrite(A1, LOW);
    digitalWrite(A2, LOW); 
    digitalWrite(B1, LOW);
    digitalWrite(B2, HIGH);
}

void stopMotors()
{
    analogWrite(EN, 0);
    digitalWrite(A1, LOW);
    digitalWrite(A2, LOW);
    digitalWrite(B1, LOW);
    digitalWrite(B2, LOW);
}

void spinRight(int spd)
{
    analogWrite(EN, spd);
    digitalWrite(A1, LOW);
    digitalWrite(A2, HIGH);
    digitalWrite(B1, HIGH);
    digitalWrite(B2, LOW);
}

float getDistance()
{
    digitalWrite(TRIG, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG, LOW);
    long duration = pulseIn(ECHO, HIGH, 15000);
    if (duration == 0)
        return 999;
    return duration * 0.034 / 2;
}