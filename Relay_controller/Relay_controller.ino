#define RELAY_PIN 15

String incomingMsg = "init";

void setup() {
  // put your setup code here, to run once:
  pinMode(15, OUTPUT);
  Serial.begin(115200);
  //Serial.begin(9600);

}

void loop() {
  // put your main code here, to run repeatedly:
  if (Serial.available() > 0) {
    incomingMsg = Serial.readStringUntil('\n');
    if (incomingMsg == "R1") {
      digitalWrite(RELAY_PIN, HIGH);
    }
    else if (incomingMsg == "R2") {
      digitalWrite(RELAY_PIN, LOW);
    }
  }
}
