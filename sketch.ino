#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>

// --- PIN DEFINITIONS ---
#define IR_L D5
#define IR_R D7
#define TRIG D6
#define ECHO D1
#define A1 D3
#define A2 D2
#define B1 D4
#define B2 D8
#define EN D0

// --- SETTINGS ---
int normalSpeed = 120;
int slowSpeed = 90;
const int TURN_MS = 240;
const int BACK_MS = 200;

// --- NETWORK ---
const char *ssid = "Ryan";
const char *password = "24274908";
IPAddress local_IP(10, 129, 134, 150);
IPAddress gateway(10, 129, 134, 126);
IPAddress subnet(255, 255, 255, 0);
ESP8266WebServer server(80);

// --- STATE ---
String current_nav = "forward";
bool target_visible = false;

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

    WiFi.config(local_IP, gateway, subnet);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED)
        delay(500);

    server.on("/forward", []()
              { current_nav = "forward"; target_visible = true; server.send(200); });
    server.on("/left", []()
              { current_nav = "left";    target_visible = true; server.send(200); });
    server.on("/right", []()
              { current_nav = "right";   target_visible = true; server.send(200); });
    server.on("/stop", []()
              { current_nav = "stop";    target_visible = false; server.send(200); });

    server.begin();
}

void loop()
{
    server.handleClient();

        int left = digitalRead(IR_L);
    int right = digitalRead(IR_R);
    float dist = getDistance();

    if (target_visible)
    {
        // --- VISION ALIGNMENT MODE ---
        if (dist < 10 && dist > 1)
        {
            stopMotors(); // STOP AT 10CM
        }
        else
        {
            int currentSpeed = (dist < 25) ? slowSpeed : normalSpeed;
            if (current_nav == "forward")
                forward(normalSpeed);
            else if (current_nav == "left")
                softLeft(currentSpeed);
            else if (current_nav == "right")
                softRight(currentSpeed);
            else
                stopMotors();
        }
    }
    else
    {
        // --- NATIVE ROAMER MODE (Obstacle Detection) ---
        if (dist < 15)
        {
            backward();
            delay(BACK_MS);
            if (left == LOW)
                softRight(normalSpeed);
            else
                softLeft(normalSpeed);
            delay(TURN_MS);
        }
        else if (left == LOW && right == HIGH)
        {
            softRight(slowSpeed);
        }
        else if (right == LOW && left == HIGH)
        {
            softLeft(slowSpeed);
        }
        else
        {
            forward(normalSpeed);
        }
    }
}

void stopMotors()
{
    analogWrite(EN, 0);
    digitalWrite(A1, LOW);
    digitalWrite(A2, LOW);
    digitalWrite(B1, LOW);
    digitalWrite(B2, LOW);
}

float getDistance()
{
    digitalWrite(TRIG, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG, LOW);
    long duration = pulseIn(ECHO, HIGH, 20000);
    if (duration == 0)
        return 999;
    return duration * 0.034 / 2;
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
    analogWrite(EN, 120);
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