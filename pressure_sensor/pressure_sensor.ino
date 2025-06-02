#include "HX711.h"

HX711 scale;

float calibration_factor = 470.0; // À ajuster ! Valeur approximative
float units;

void setup() {
  Serial.begin(9600);
  scale.begin(2, 4); // DT, CLK

  Serial.println("⚖️ Calibration HX711");
  Serial.println("1. Retirer tout poids → tare");
  delay(3000);

  scale.set_scale();  // pas de facteur pour l'instant
  scale.tare();       // remise à zéro

  Serial.println("2. Placer un poids connu !");
  Serial.println("Appuie sur 'a' pour augmenter, 'z' pour diminuer le facteur.");
}

void loop() {
  scale.set_scale(calibration_factor);
  units = scale.get_units();

  Serial.print("Lecture : ");
  Serial.print(units, 1);  // une décimale
  Serial.print(" g  | facteur = ");
  Serial.println(calibration_factor);

  if (Serial.available()) {
    char key = Serial.read();
    if (key == 'a') calibration_factor += 10;
    else if (key == 'z') calibration_factor -= 10;
  }

  delay(500);
}


