#include <ESP8266WiFi.h>
#include <ESP8266WiFiMulti.h>
#include <WiFiUdp.h>

// Pin Definitions
#define LIGHT_SENSOR_PIN A0       // Analog light sensor
#define LED_INDICATOR 0           // External LED to indicate brightness
#define MASTER_INDICATOR 2        // Onboard LED to indicate master status (active-low)

// Network and Communication Settings
#define BROADCAST_PORT 4210
#define UDP_PACKET_SIZE 50

ESP8266WiFiMulti WiFiMulti;
WiFiUDP udp;

String broadcastIP = "255.255.255.255"; // Broadcast IP for ESP communication
int lightReading = 0;
bool isMaster = false;
unsigned long lastBroadcastTime = 0;
const int broadcastInterval = 100; // in ms

void setup() {
  Serial.begin(115200);

  // WiFi Connection Setup
  WiFiMulti.addAP("rohan", "12345678"); // Replace with your network credentials
  while (WiFiMulti.run() != WL_CONNECTED) {
    delay(100);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");

  // Begin UDP Communication
  udp.begin(BROADCAST_PORT);

  // Pin Mode Setup
  pinMode(LIGHT_SENSOR_PIN, INPUT);
  pinMode(LED_INDICATOR, OUTPUT);
  pinMode(MASTER_INDICATOR, OUTPUT);

  // Ensure Master LED is off initially (active-low logic)
  digitalWrite(MASTER_INDICATOR, HIGH);
}

void loop() {
  // Read Light Sensor Value
  lightReading = analogRead(LIGHT_SENSOR_PIN);

  // Adjust External LED Brightness Using PWM
  int pwmValue = map(lightReading, 0, 1023, 0, 255); // Map sensor readings to PWM range
  analogWrite(LED_INDICATOR, pwmValue);

  // Broadcast Light Reading Periodically
  if (millis() - lastBroadcastTime > broadcastInterval) {
    broadcastLightReading();
    lastBroadcastTime = millis();
    Serial.println("Broadcasting light reading: " + String(lightReading));
  }

  // Listen for Other ESP Broadcasts
  int packetSize = udp.parsePacket();
  if (packetSize) {
    char packetBuffer[UDP_PACKET_SIZE];
    udp.read(packetBuffer, UDP_PACKET_SIZE);
    int otherReading = String(packetBuffer).toInt();
    Serial.println("Received light reading: " + String(otherReading));

    // Determine Master Based on Highest Light Reading
    if (otherReading > lightReading) {
      isMaster = false;
      digitalWrite(MASTER_INDICATOR, HIGH); // Turn Off Master LED if Not Master
      Serial.println("Another ESP has a higher reading. Not the Master.");
    } else {
      isMaster = true;
    }
  }

  // Update Master LED State
  if (isMaster) {
    digitalWrite(MASTER_INDICATOR, LOW); // Turn On Master LED if Master
    sendMasterData();
  }
}

// Function to Broadcast Light Reading to the Swarm
void broadcastLightReading() {
  String reading = String(lightReading);
  udp.beginPacket(broadcastIP.c_str(), BROADCAST_PORT);
  udp.write(reading.c_str());
  udp.endPacket();
}

// Function to Send Data to Raspberry Pi or Log Master's Status
void sendMasterData() {
  // Master Status Information
  Serial.println("==== MASTER STATUS ====");
  Serial.println("Device IP: " + WiFi.localIP().toString());
  Serial.println("Light Reading: " + String(lightReading));
  Serial.println("=======================");
}
