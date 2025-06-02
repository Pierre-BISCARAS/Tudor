#define buzzerPin 3

// Heure de réveil simulée (ex: 7h30)
int wakeHour = 0;
int wakeMinute = 1;

unsigned long startMillis;
bool alarmTriggered = false;

void setup() {
  Serial.begin(9600);
  pinMode(buzzerPin, OUTPUT);
  digitalWrite(buzzerPin, LOW);

  startMillis = millis();
  Serial.println("⏰ Test alarme démarré");
}

void loop() {
  unsigned long elapsedMinutes = (millis() - startMillis) / 60000;
  int currentHour = (elapsedMinutes / 60) % 24;
  int currentMinute = elapsedMinutes % 60;

  Serial.print("🕒 Heure simulée : ");
  Serial.print(currentHour);
  Serial.print("h");
  Serial.println(currentMinute);

  // Déclenchement de l'alarme si heure atteinte
  if (!alarmTriggered && currentHour == wakeHour && currentMinute == wakeMinute) {
    Serial.println("🔔 Réveil ! Déclenchement du buzzer...");
    for (int i = 0; i < 5; i++) {
      digitalWrite(buzzerPin, HIGH);
      delay(300);
      digitalWrite(buzzerPin, LOW);
      delay(200);
    }
    alarmTriggered = true; // éviter répétition
  }

  delay(5000); // Vérifie toutes les 5 secondes
}
