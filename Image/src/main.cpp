#include <Arduino.h>

#define terminal Serial

const int PIN_CLK = 13;
const int PIN_CLR = 12;
const int AD7680_SPI_CS = 11;
const int AD7680_SPI_MISO = 10;
const int AD7680_SPI_CLK = 9;

// ── 快速 GPIO 宏（直接写寄存器，单周期操作） ──
#define CS_HIGH   GPIO.out_w1ts = (1UL << AD7680_SPI_CS)
#define CS_LOW    GPIO.out_w1tc = (1UL << AD7680_SPI_CS)
#define SCLK_HIGH GPIO.out_w1ts = (1UL << AD7680_SPI_CLK)
#define SCLK_LOW  GPIO.out_w1tc = (1UL << AD7680_SPI_CLK)
#define MISO_BIT  ((GPIO.in >> AD7680_SPI_MISO) & 1)
#define MCLK_HIGH GPIO.out_w1ts = (1UL << PIN_CLK)
#define MCLK_LOW  GPIO.out_w1tc = (1UL << PIN_CLK)
#define MCLR_HIGH GPIO.out_w1ts = (1UL << PIN_CLR)
#define MCLR_LOW  GPIO.out_w1tc = (1UL << PIN_CLR)
// 时序延迟: ~40ns @240MHz，满足 AD7680 最小 20ns 建立/保持时间
#define TICK      asm volatile("nop; nop; nop; nop; nop; nop; nop; nop; nop; nop;")

#define MAX_FRAMES 60
uint16_t frames[MAX_FRAMES][64];

int pixelOrder[] = {26, 27, 18, 19, 10, 11, 2, 3, 1, 0, 9, 8, 17, 16, 25, 24};
int subtileOrder[] = {0, 2, 1, 3};
int subtileOffset[] = {0, 4, 32, 36};
uint16_t frame[64];

#define MODE_IDLE       0
#define MODE_LIVE       1
#define MODE_HIGHSPEED1 2
#define MODE_HIGHSPEED2 3
#define MODE_HIGHSPEED3 4
#define MODE_HIGHSPEED4 5
#define MODE_PIXEL      6
#define MODE_VERIFY     7

const int ANALOG_PIN = 8;
int curMode = MODE_IDLE;

uint32_t readAD7680Raw() {
  uint32_t value = 0;
  CS_HIGH; TICK; TICK;         // t_CSH ≥ 80ns
  SCLK_LOW;
  CS_LOW;
  for (int i = 0; i < 20; i++) {
    value = (value << 1) | MISO_BIT;
    SCLK_HIGH; TICK;
    SCLK_LOW;  TICK;
  }
  CS_HIGH;
  return value;
}

uint16_t readAD7680() {
  return (uint16_t)(readAD7680Raw() & 0xFFFF);
}

int readMagnetometer() {
  return readAD7680();
}

void clearCounter() {
  MCLR_LOW;  delayMicroseconds(1);
  MCLR_HIGH; delayMicroseconds(1);
}

void incrementCounter() {
  MCLK_HIGH; delayMicroseconds(1);
  MCLK_LOW;  delayMicroseconds(1);
}

void readTileFrame() {
  clearCounter();
  incrementCounter();
  for (int curSubtileIdx = 0; curSubtileIdx < 4; curSubtileIdx++) {
    for (int curIdx = 0; curIdx < 16; curIdx++) {
      int value = readMagnetometer();
      int frameOffset = pixelOrder[curIdx] + subtileOffset[subtileOrder[curSubtileIdx]];
      frame[frameOffset] = value;
      incrementCounter();
    }
  }
}

void displayCurrentFrame() {
  int idx = 0;
  for (int i = 0; i < 8; i++) {
    for (int j = 0; j < 8; j++) {
      terminal.print(frame[idx]);
      terminal.print(" ");
      idx += 1;
    }
    terminal.println("");
  }
  terminal.println("*");
}

void recordHighSpeedFrames(int frameDelayTime) {
  terminal.println("REC_START");
  long startTime = millis();
  for (int f = 0; f < MAX_FRAMES; f++) {
    readTileFrame();
    for (int a = 0; a < 64; a++) {
      frames[f][a] = frame[a];
    }
    if (frameDelayTime > 0) {
      delay(frameDelayTime);
    }
    if ((f + 1) % 20 == 0) {
      terminal.print("REC ");
      terminal.print(f + 1);
      terminal.println("/60");
    }
  }
  long endTime = millis();
  float fps = (float)MAX_FRAMES / ((float)(endTime - startTime) / 1000.0f);
  terminal.print("REC_DONE fps=");
  terminal.println(fps);
}

void playbackHighSpeedFrames() {
  terminal.println("PLAY_START");
  for (int f = 0; f < MAX_FRAMES; f++) {
    int idx = 0;
    for (int i = 0; i < 8; i++) {
      for (int j = 0; j < 8; j++) {
        terminal.print(frames[f][idx]);
        terminal.print(" ");
        idx += 1;
      }
      terminal.println("");
    }
    terminal.println("*");
    delay(50);
  }
  terminal.println("PLAY_DONE");
}

void setup() {
  pinMode(PIN_CLR, OUTPUT);
  pinMode(PIN_CLK, OUTPUT);
  pinMode(AD7680_SPI_CS, OUTPUT);
  pinMode(AD7680_SPI_CLK, OUTPUT);
  pinMode(AD7680_SPI_MISO, INPUT);

  incrementCounter();
  clearCounter();

  terminal.begin(921600);
  delay(1000);

  terminal.println("Initializing... Press L (live) or H (high speed), 1, 2, 3, 4, or S (idle)");

  clearCounter();
  incrementCounter();
  delay(100);
}

void loop() {
  if (terminal.available()) {
    byte incoming = terminal.read();

    if (incoming == 'L') {
      terminal.println("Live");
      curMode = MODE_LIVE;
    } else if (incoming == 'H' || incoming == '1') {
      terminal.println("High-speed Save1 (max)");
      curMode = MODE_HIGHSPEED1;
    } else if (incoming == '2') {
      terminal.println("High-speed Save2 (1ms)");
      curMode = MODE_HIGHSPEED2;
    } else if (incoming == '3') {
      terminal.println("High-speed Save3 (2ms)");
      curMode = MODE_HIGHSPEED3;
    } else if (incoming == '4') {
      terminal.println("High-speed Save4 (4ms)");
      curMode = MODE_HIGHSPEED4;
    } else if (incoming == 'S') {
      terminal.println("Idle");
      curMode = MODE_IDLE;
    } else if (incoming == 'P') {
      terminal.println("Read Pixel 0,0");
      curMode = MODE_PIXEL;
    } else if (incoming == 'V') {
      terminal.println("Verify - reading AD7680 vs ESP32 ADC");
      curMode = MODE_VERIFY;
    }
  }

  if (curMode == MODE_LIVE) {
    readTileFrame();
    displayCurrentFrame();
    delay(12);  // ~60 Hz

  } else if (curMode == MODE_HIGHSPEED1) {
    recordHighSpeedFrames(0);
    playbackHighSpeedFrames();
    curMode = MODE_IDLE;
    terminal.println("Initializing... Press L (live) or H (high speed), 1, 2, 3, 4, or S (idle)");

  } else if (curMode == MODE_HIGHSPEED2) {
    recordHighSpeedFrames(1);
    playbackHighSpeedFrames();
    curMode = MODE_IDLE;
    terminal.println("Initializing... Press L (live) or H (high speed), 1, 2, 3, 4, or S (idle)");

  } else if (curMode == MODE_HIGHSPEED3) {
    recordHighSpeedFrames(2);
    playbackHighSpeedFrames();
    curMode = MODE_IDLE;
    terminal.println("Initializing... Press L (live) or H (high speed), 1, 2, 3, 4, or S (idle)");

  } else if (curMode == MODE_HIGHSPEED4) {
    recordHighSpeedFrames(4);
    playbackHighSpeedFrames();
    curMode = MODE_IDLE;
    terminal.println("Initializing... Press L (live) or H (high speed), 1, 2, 3, 4, or S (idle)");

  } else if (curMode == MODE_PIXEL) {
    curMode = MODE_IDLE;
    terminal.println("Initializing... Press L (live) or H (high speed), 1, 2, 3, 4, or S (idle)");

  } else if (curMode == MODE_VERIFY) {
    uint32_t raw = readAD7680Raw();
    uint16_t ad7680_val = (uint16_t)(raw & 0xFFFF);
    int esp32_raw = analogRead(ANALOG_PIN);
    int esp32_mv = analogReadMilliVolts(ANALOG_PIN);

    terminal.print("raw[");
    for (int b = 19; b >= 0; b--) {
      terminal.print((raw >> b) & 0x01);
      if (b == 16 || b == 4) terminal.print("|");
    }
    terminal.print("] val=");
    terminal.print(ad7680_val);
    terminal.print(" | ESP32: ");
    terminal.print(esp32_raw);
    terminal.print(" (");
    terminal.print(esp32_mv);
    terminal.println("mV)");
    delay(200);
  }
}
