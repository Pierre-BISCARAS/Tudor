#define ECG_PIN A0   // sortie analogique ECG
#define LO_PLUS 11   // LO+
#define LO_MINUS 10  // LO-

unsigned long lastBeatTime = 0;
unsigned long beatInterval = 0;
int bpm = 0;

const int threshold = 512;  // Seuil de détection R-peak
bool previousState = false;

void setup() {
  Serial.begin(9600);
  pinMode(ECG_PIN, INPUT);
  pinMode(LO_PLUS, INPUT);
  pinMode(LO_MINUS, INPUT);

  Serial.println("🫀 Lecture ECG + Lead-Off (AD8232)");
}

void loop() {
  // Vérifie si les électrodes sont bien connectées
  if (digitalRead(LO_PLUS) == HIGH || digitalRead(LO_MINUS) == HIGH) {
    Serial.println("⚠️ Electrodes non connectées !");
    delay(1000);
    return;
  }

  // Lire la valeur ECG
  int ecgValue = analogRead(ECG_PIN);
  bool currentState = ecgValue > threshold;

  // Détection de front montant (battement)
  if (currentState && !previousState) {
    unsigned long now = millis();
    beatInterval = now - lastBeatTime;
    lastBeatTime = now;

    if (beatInterval > 300 && beatInterval < 1500) {
      bpm = 60000 / beatInterval;
      Serial.print("❤️ BPM : ");
      Serial.println(bpm);
    }
  }

  previousState = currentState;

  delay(5);  // fréquence d’échantillonnage rapide
}
