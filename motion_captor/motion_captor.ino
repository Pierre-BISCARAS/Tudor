#define PIR 2
#define LED 13

void setup() {
  pinMode(PIR, INPUT);
  pinMode(LED, OUTPUT);
}

void loop() {
   int pirVal = digitalRead(PIR);

   if (pirVal == HIGH) {
      digitalWrite(LED, HIGH);
      Serial.println("HIGH");
   }

   else {
      digitalWrite(LED,LOW);
      Serial.println("LOW");
   }

}


