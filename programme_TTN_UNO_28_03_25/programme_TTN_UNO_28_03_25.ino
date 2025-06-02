#include <DHT11.h>
#include <Wire.h>
#include <TheThingsNetwork.h>
#include "HX711.h"

const char* appEui = "0206200319112003";
const char* appKey = "D29C0C1C9DECD24D8EE7BA0D6BDDD040";

#define DHTPIN 2
#define PIRPIN 4
#define LED 13
#define HX_DT 6
#define HX_SCK 7
#define ECG_PIN A0
#define LO_PLUS 10
#define LO_MINUS 11
#define BUZZER_PIN 3
#define FAN 8

#define loraSerial Serial1
#define debugSerial Serial
#define freqPlan TTN_FP_EU868

DHT11 dht(DHTPIN);
HX711 scale;
TheThingsNetwork ttn(loraSerial, debugSerial, freqPlan);

// Mesure BPM
unsigned long lastBeatTime = 0;
int bpm = 0;
bool previousECGState = false;
const int ecgThreshold = 520;
bool electrodesConnected = false;

// Données capteurs
int lastTemperature = 0;
int lastHumidity = 0;
int lastPresence = 0;
float lastWeight = 0.0;
int bpmToSend = 0;
float calibration_factor = 470.0;

// Réveil
int wakeHour = -1;
int wakeMinute = -1;
bool alarmTriggered = false;
unsigned long startMillis = 0;

unsigned long lastECGCheck = 0;
unsigned long lastTTNSend = 0;


void message(const byte* payload, int length, int port);

void setup() {
  debugSerial.begin(9600);
  loraSerial.begin(57600);

  pinMode(PIRPIN, INPUT);
  pinMode(LED, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(ECG_PIN, INPUT);
  pinMode(LO_PLUS, INPUT);
  pinMode(LO_MINUS, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(FAN, OUTPUT);

  digitalWrite(BUZZER_PIN, LOW);


  scale.begin(HX_DT, HX_SCK);
  scale.set_scale(calibration_factor);
  scale.tare();

  delay(2000);
  ttn.showStatus();
  ttn.join(appEui, appKey);
  ttn.onMessage(message);

  startMillis = millis();
  debugSerial.println("⏱️ Mode accéléré activé : 1 min simulée = 5s");

  tone(BUZZER_PIN, 1500);
  delay(300);
  noTone(BUZZER_PIN);
}

void loop() {
  unsigned long now = millis();
  

  // 🕒 Simulation du temps
  unsigned long elapsedMinutes = (now - startMillis) / 5000;
  int currentHour = (elapsedMinutes / 60) % 24;
  int currentMinute = elapsedMinutes % 60;

  debugSerial.print("🕒 Heure simulée : ");
  debugSerial.print(currentHour);
  debugSerial.print("h");
  debugSerial.println(currentMinute);

  debugSerial.print("⏰ Vérif alarme : ");
  debugSerial.print(currentHour);
  debugSerial.print("h");
  debugSerial.print(currentMinute);
  debugSerial.print(" vs ");
  debugSerial.print(wakeHour);
  debugSerial.print("h");
  debugSerial.println(wakeMinute);

  if (!alarmTriggered && currentHour == wakeHour && currentMinute == wakeMinute) {
    debugSerial.println("🔔 ALARME : heure atteinte !");
    for (int i = 0; i < 5; i++) {
      tone(BUZZER_PIN, 1000);
      delay(300);
      noTone(BUZZER_PIN);
      delay(200);
    }
    alarmTriggered = true;
  }

  // 💓 Mesure BPM
  if (now - lastECGCheck >= 5) {
    lastECGCheck = now;
    int ecgValue = analogRead(ECG_PIN);
    electrodesConnected = (digitalRead(LO_PLUS) == LOW && digitalRead(LO_MINUS) == LOW);
    if (electrodesConnected) {
      bool currentECGState = ecgValue > ecgThreshold;
      if (currentECGState && !previousECGState) {
        unsigned long beatInterval = now - lastBeatTime;
        lastBeatTime = now;
        if (beatInterval > 300 && beatInterval < 1500) {
          bpm = 60000 / beatInterval;
          bpmToSend = bpm;
          digitalWrite(LED_BUILTIN, HIGH);
          delay(20);
          digitalWrite(LED_BUILTIN, LOW);
        }
      }
      previousECGState = currentECGState;
    } else {
      bpmToSend = 0;
    }
  }

  if (lastTemperature > 26) {
    digitalWrite(FAN, HIGH);
  }
  else {
   digitalWrite(FAN, LOW); 
  }
  // 📤 Envoi TTN + collecte toutes les 10s
  if (now - lastTTNSend >= 10000) {
    lastTTNSend = now;

    lastTemperature = dht.readTemperature();
    delay(2000);
    float lastHumidity = dht.readHumidity();
    if (lastTemperature < -20 || lastTemperature > 80) lastTemperature = 0;


    lastPresence = digitalRead(PIRPIN);
    digitalWrite(LED, lastPresence);

    scale.set_scale(calibration_factor);
    lastWeight = scale.get_units();
    if (lastWeight < 0) lastWeight = 0;
    uint16_t poids_encoded = (uint16_t)(lastWeight * 10);

    uint8_t payload[6];
    payload[0] = (uint8_t)lastTemperature;
    payload[1] = (uint8_t)lastHumidity;
    payload[2] = (uint8_t)(lastPresence ? 1 : 0);
    payload[3] = poids_encoded & 0xFF;
    payload[4] = (poids_encoded >> 8) & 0xFF;
    payload[5] = (uint8_t)bpmToSend;

    debugSerial.print("📦 Temp: ");
    debugSerial.print(lastTemperature);
    debugSerial.print(" °C | Hum: ");
    debugSerial.print(lastHumidity);
    debugSerial.print(" % | PIR: ");
    debugSerial.print(lastPresence ? "OUI" : "NON");
    debugSerial.print(" | Poids: ");
    debugSerial.print(lastWeight, 1);
    debugSerial.print(" g | BPM: ");
    debugSerial.println(bpmToSend);

    ttn.sendBytes(payload, sizeof(payload));
  }
}


void message(const byte* payload, int length, int port) {
  debugSerial.println("-- MESSAGE TTN reçu --");

  debugSerial.print("Port : ");
  debugSerial.println(port);

  debugSerial.print("Payload : ");
  for (int i = 0; i < length; i++) {
    debugSerial.print(payload[i], HEX);
    debugSerial.print(" ");
  }
  debugSerial.println();

  if (length >= 2) {
    wakeHour = payload[0];
    wakeMinute = payload[1];
    alarmTriggered = false;

    debugSerial.print("📩 Réveil reçu : ");
    debugSerial.print(wakeHour);
    debugSerial.print("h");
    debugSerial.println(wakeMinute);
  }
}
