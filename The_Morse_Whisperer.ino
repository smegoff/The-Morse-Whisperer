/*
  The Morse Whisperer (Heltec WiFi LoRa 32 V3)
  ------------------------------------------------------------
  CW decoder with:
   - Goertzel tone detector (ADC audio in)
   - Adaptive dot timing + RAW/EXPANDED text
   - SNR + SNR bar (OLED)
   - Squelch (SNR-based gate)
   - PRG button menu (single button, deterministic behaviour)
   - SoftAP Wi-Fi + mobile-friendly Web UI
   - LoRa radio ON/OFF toggle (OFF by default)  [RadioLib if installed]
   - Menu option to show QR code to join Wi-Fi AP (no main-screen squeeze)
   - OLED power saver: sleep after 5 mins inactivity, wake on activity ✅

  Board: Heltec WiFi LoRa 32 (V3) / Heltec-esp32 core 3.x

  Libraries:
   - U8g2 (required)
   - WiFi / WebServer (core)
   - RadioLib (optional, for SX1262 LoRa ON/OFF)
   - QR code:
       * Works with ESP32 core "qrcode.h" (esp_qrcode_* API) OR
       * Works with Richard Moore "qrcode.h" (QRCode/qrcode_* API)
     This sketch auto-detects which one you have.

  LoRa pins (Heltec WiFi LoRa 32 V3, per common schematic-based mapping):
    NSS/CS=8, RST=12, DIO1=14, BUSY=13, SCK=9, MISO=11, MOSI=10

  OLED pins (typical):
    SDA=17, SCL=18, RST=21

  VEXT: some Heltec revisions need VEXT enabled for OLED rail.
*/

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <U8g2lib.h>
#include <SPI.h>

#if __has_include(<RadioLib.h>)
  #include <RadioLib.h>
  #define HAVE_RADIOLIB 1
#else
  #define HAVE_RADIOLIB 0
#endif

// QR library detection (supports either ESP32 core or RicMoo)
#if __has_include("qrcode.h")
  #include "qrcode.h"
  #define HAVE_QRCODE_H 1
#else
  #define HAVE_QRCODE_H 0
#endif

// ESP32 core "qrcode.h" typically defines ESP_QRCODE_CONFIG_DEFAULT()
#if HAVE_QRCODE_H && defined(ESP_QRCODE_CONFIG_DEFAULT)
  #define QR_IMPL_ESP 1
#else
  #define QR_IMPL_ESP 0
#endif

// RicMoo "qrcode.h" typically defines QRCode struct + qrcode_* functions (no ESP_QRCODE_CONFIG_DEFAULT)
#if HAVE_QRCODE_H && !QR_IMPL_ESP
  #define QR_IMPL_RICMOO 1
#else
  #define QR_IMPL_RICMOO 0
#endif

// ============================================================================
// Arduino prototype safety section
// MUST appear before any function using TonePick
// ============================================================================
typedef struct TonePick {
  float freq;
  float mag;
} TonePick;

// ===================== Project Identity =====================
static const char* PROJECT_NAME = "The Morse Whisperer";
static const char* PROJECT_TAG  = "Beep -> Words";
static const char* VERSION_STR  = "v1.0 (stable build)";

// ===================== Wi-Fi AP =============================
// PATCH: rename SSID to match project (and fix web UI text below)
static const char* AP_SSID = "The Morse Whisperer";
static const char* AP_PASS = "cwdecode123";     // 8+ chars required for WPA2

// ===================== Board Pins (Heltec V3) ===============
// OLED: SDA=GPIO17, SCL=GPIO18, RST=GPIO21
static const int PIN_OLED_SDA = 17;
static const int PIN_OLED_SCL = 18;
static const int PIN_OLED_RST = 21;

// Vext control often GPIO36 (polarity varies)
static const int PIN_VEXT_CTRL = 36;
static const int VEXT_ON_LEVEL = LOW;  // try LOW first, flip to HIGH if needed

// PRG / USER button often GPIO0 (active LOW)
static const int PIN_PRG_BTN = 0;

// Audio ADC pin: choose a known-good ADC-capable pin on your specific Heltec V3.
static const int ADC_PIN = 4;

// LoRa SX1262 pins (Heltec WiFi LoRa 32 V3)
static const int LORA_NSS  = 8;
static const int LORA_RST  = 12;
static const int LORA_DIO1 = 14;
static const int LORA_BUSY = 13;
static const int LORA_SCK  = 9;
static const int LORA_MISO = 11;
static const int LORA_MOSI = 10;

// ===================== Decoder Settings ======================
static const int   SAMPLE_RATE = 8000;  // Hz
static const int   BLOCK_N     = 160;   // 20ms blocks at 8kHz
static float       targetToneHz = 700.0f; // Hz
static float       sensitivity  = 1.00f;  // 0.50 .. 2.00
static float       squelchSNR   = 1.20f;  // 1.00 .. 6.00 (SNR ratio gate)

// Timing thresholds (in dot units)
static const float DAH_DOT_RATIO_CUTOFF = 2.0f;
static const float LETTER_GAP_UNITS     = 3.0f;
static const float WORD_GAP_UNITS       = 7.0f;

// Adaptive dot estimation
static float dotMs = 60.0f;          // initial guess (~20WPM)
static const float DOT_EMA_ALPHA = 0.12f;
static const int   MARK_HISTORY  = 24;
static float markDurations[MARK_HISTORY];
static int   markCount = 0;
static int   markIdx   = 0;

// ===================== OLED ================================
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(
  U8G2_R0,
  /* reset = */ PIN_OLED_RST,
  /* clock = */ PIN_OLED_SCL,
  /* data  = */ PIN_OLED_SDA
);

// ===================== Web Server ==========================
WebServer server(80);

// ===================== UI State ============================
static bool trainingMode    = false;
static bool expandShorthand = true;

// decoded buffers (bounded)
static String decodedRaw = "";
static String decodedExpanded = "";
static String currentWord = "";
static String currentSymbol = "";

// ===================== Goertzel State =======================
static float goertzel_coeff = 0.0f;
static float goertzel_sine  = 0.0f;
static float goertzel_cosine= 0.0f;

// Detector / envelopes / SNR
static float noiseFloor  = 0.0f;
static float signalFloor = 0.0f;
static float detectLevel = 0.0f;
static float thrOn       = 0.0f;
static float thrOff      = 0.0f;
static bool  tonePresent = false;

static float snrEma = 1.0f; // SNR ratio EMA
static uint32_t lastTransitionMs = 0;

// ===================== PRG Button (Menu Controls) ===========
static const uint32_t HOLD_1S_MS = 1000;
static const uint32_t HOLD_2S_MS = 2000;

enum BtnEvent : uint8_t { BTN_NONE=0, BTN_SHORT=1, BTN_HOLD1=2, BTN_PANIC=3 };
static bool     btnDown = false;
static uint32_t btnDownMs = 0;
static bool     panicFired = false;

enum UiScreen : uint8_t {
  SCREEN_MAIN = 0,
  SCREEN_MENU,
  SCREEN_ADJ_TONE,
  SCREEN_ADJ_SENS,
  SCREEN_ADJ_SQL,
  SCREEN_QR
};
static UiScreen uiScreen = SCREEN_MAIN;

enum MenuItem : uint8_t {
  MI_TRAIN = 0,
  MI_EXPAND,
  MI_CALIBRATE,
  MI_TONE,
  MI_SENS,
  MI_SQUELCH,
  MI_LORA,
  MI_QR,
  MI_CLEAR,
  MI_EXIT,
  MI_COUNT
};
static uint8_t menuIdx = 0;

// QR screen timer (optional auto-return)
static uint32_t qrEnterMs = 0;

// ===================== OLED Power Saver =====================
// PATCH: sleep OLED after 5 mins of no input activity, wake instantly on activity.
static const uint32_t OLED_SLEEP_MS = 5UL * 60UL * 1000UL; // 5 minutes
static uint32_t lastActivityMs = 0;
static bool oledSleeping = false;

static void noteActivity() {
  lastActivityMs = millis();
  if (oledSleeping) {
    oledSleeping = false;
    u8g2.setPowerSave(0); // wake OLED
  }
}

static void oledSleepCheck() {
  if (!oledSleeping && (millis() - lastActivityMs) > OLED_SLEEP_MS) {
    oledSleeping = true;
    u8g2.setPowerSave(1); // sleep OLED
  }
}

// ============================================================================
// Forward declarations
// ============================================================================
static BtnEvent pollPrgButtonEvent();
static void uiPanicToMain();
static void menuSelect(MenuItem mi);
static void oledRender();
static void processBlock();
static void calibrateNow();
static void computeGoertzelForFreq(float freqHz);
static void resetDetectorFloors();
static float goertzelMagnitude(const int16_t* x, int N);
static TonePick autoFindTone(const int16_t* block, int N);
static void setLoRaEnabled(bool on);
static void webBegin();

// QR helpers
static void oledQrJoinScreen();
static String wifiQrPayload(const String& ssid, const String& pass);
static String wifiQrEscape(const String& s);

// ===================== International Morse Table ============
struct MorseMap { const char* sym; char ch; };
static const MorseMap MORSE_TABLE[] = {
  {".-", 'A'},   {"-...", 'B'}, {"-.-.", 'C'}, {"-..", 'D'},  {".", 'E'},
  {"..-.", 'F'}, {"--.", 'G'},  {"....", 'H'}, {"..", 'I'},   {".---", 'J'},
  {"-.-", 'K'},  {".-..", 'L'}, {"--", 'M'},   {"-.", 'N'},   {"---", 'O'},
  {".--.", 'P'}, {"--.-", 'Q'}, {".-.", 'R'},  {"...", 'S'},  {"-", 'T'},
  {"..-", 'U'},  {"...-", 'V'}, {".--", 'W'},  {"-..-", 'X'}, {"-.--", 'Y'},
  {"--..", 'Z'},
  {"-----",'0'}, {".----",'1'}, {"..---",'2'}, {"...--",'3'}, {"....-",'4'},
  {".....",'5'}, {"-....",'6'}, {"--...",'7'}, {"---..",'8'}, {"----.",'9'},
  {".-.-.-",'.'}, {"--..--",','}, {"..--..",'?'}, {".----.",'\''},
  {"-.-.--",'!'}, {"-..-.",'/'},  {"-.--.",'('},  {"-.--.-",')'},
  {".-...",'&'},  {"---...",':'}, {"-.-.-.",';'}, {"-...-", '='},
  {".-.-.",'+'},  {"-....-",'-'}, {"..--.-",'_'}, {".-..-.",'"'},
  {".--.-.",'@'}
};

static char decodeMorse(const String& s) {
  for (size_t i = 0; i < sizeof(MORSE_TABLE)/sizeof(MORSE_TABLE[0]); i++) {
    if (s.equals(MORSE_TABLE[i].sym)) return MORSE_TABLE[i].ch;
  }
  return 0;
}

// ===================== Shorthand Expansion ==================
struct Abbrev { const char* key; const char* val; };
static const Abbrev ABBREV[] = {
  {"CQ",  "Calling any station"},
  {"DE",  "from"},
  {"K",   "over"},
  {"KN",  "over (specific)"},
  {"AR",  "end of message"},
  {"SK",  "silent key / end"},
  {"BK",  "break"},
  {"R",   "roger"},
  {"RR",  "roger roger"},
  {"UR",  "your"},
  {"TNX", "thanks"},
  {"THX", "thanks"},
  {"73",  "best regards"},
  {"OM",  "old man"},
  {"YL",  "young lady"},
  {"HW",  "how copy?"},
  {"QTH", "location"},
  {"QRM", "interference"},
  {"QRN", "noise"},
  {"QRS", "send slower"},
  {"QRO", "increase power"},
  {"QRP", "low power"},
};

static String expandWord(const String& w) {
  if (!expandShorthand) return w;
  String up = w;
  up.toUpperCase();
  for (size_t i = 0; i < sizeof(ABBREV)/sizeof(ABBREV[0]); i++) {
    if (up.equals(ABBREV[i].key)) return String(ABBREV[i].val);
  }
  return w;
}

// ===================== Helpers ==============================
static float wpmEstimate() {
  if (dotMs < 1.0f) return 0.0f;
  return 1200.0f / dotMs;
}

static void clampBuffers() {
  const int MAX_RAW = 1200;
  const int MAX_EXP = 2200;
  if (decodedRaw.length() > MAX_RAW) decodedRaw.remove(0, decodedRaw.length() - MAX_RAW);
  if (decodedExpanded.length() > MAX_EXP) decodedExpanded.remove(0, decodedExpanded.length() - MAX_EXP);
}

static String jsonEscape(const String& s) {
  String out;
  out.reserve(s.length() + 16);
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    switch (c) {
      case '\\': out += "\\\\"; break;
      case '"':  out += "\\\""; break;
      case '\n': out += "\\n";  break;
      case '\r': out += "\\r";  break;
      case '\t': out += "\\t";  break;
      default:
        if ((uint8_t)c < 0x20) out += ' ';
        else out += c;
    }
  }
  return out;
}

static float clampf(float v, float lo, float hi) {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

// ===================== LoRa Radio (optional) =================
static bool loraEnabled = false; // OFF by default

#if HAVE_RADIOLIB
  SX1262 radio = new Module(LORA_NSS, LORA_DIO1, LORA_RST, LORA_BUSY);
  static bool loraInited = false;

  static bool loraStart() {
    if (!loraInited) {
      SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);
      int state = radio.begin(915.0);
      if (state != RADIOLIB_ERR_NONE) {
        Serial.printf("[LORA] init failed: %d\n", state);
        return false;
      }
      loraInited = true;
    }
    radio.standby();
    Serial.println("[LORA] ON");
    return true;
  }

  static void loraStop() {
    if (!loraInited) return;
    radio.sleep();
    Serial.println("[LORA] OFF");
  }
#else
  static bool loraStart() { Serial.println("[LORA] N/A (RadioLib missing)"); return false; }
  static void loraStop()  { Serial.println("[LORA] N/A (RadioLib missing)"); }
#endif

static void setLoRaEnabled(bool on) {
  if (on == loraEnabled) return;
  if (on) {
    if (loraStart()) loraEnabled = true;
  } else {
    loraStop();
    loraEnabled = false;
  }
}

static const char* loraStatusText() {
#if HAVE_RADIOLIB
  return loraEnabled ? "ON" : "OFF";
#else
  return "N/A";
#endif
}

// ===================== OLED UI ==============================
static void drawBar(int x, int y, int w, int h, float frac01) {
  frac01 = clampf(frac01, 0.0f, 1.0f);
  u8g2.drawFrame(x, y, w, h);
  int fillW = (int)floorf((w - 2) * frac01);
  if (fillW < 0) fillW = 0;
  if (fillW > (w - 2)) fillW = (w - 2);
  u8g2.drawBox(x + 1, y + 1, fillW, h - 2);
}

static void oledSplash() {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x12_tr);
  u8g2.drawStr(0, 12, PROJECT_NAME);
  u8g2.drawStr(0, 26, PROJECT_TAG);
  u8g2.drawStr(0, 40, VERSION_STR);
  u8g2.drawStr(0, 58, "Hold PRG=Menu");
  u8g2.sendBuffer();
}

static const char* menuItemLabel(uint8_t idx) {
  switch ((MenuItem)idx) {
    case MI_TRAIN:    return "Training";
    case MI_EXPAND:   return "Expand";
    case MI_CALIBRATE:return "Calibrate";
    case MI_TONE:     return "Tone";
    case MI_SENS:     return "Sensitivity";
    case MI_SQUELCH:  return "Squelch";
    case MI_LORA:     return "LoRa Radio";
    case MI_QR:       return "Wi-Fi QR";
    case MI_CLEAR:    return "Clear";
    case MI_EXIT:     return "Exit";
    default:          return "";
  }
}

static void oledRenderMain() {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x12_tr);

  String l1 = String(trainingMode ? "TRAIN" : "RX") +
              "  " + String((int)targetToneHz) + "Hz" +
              "  " + String(wpmEstimate(), 1) + "WPM";
  u8g2.drawStr(0, 12, l1.c_str());

  String l2 = "SNRx" + String(snrEma, 2) + "  LORA:" + String(loraStatusText());
  u8g2.drawStr(0, 26, l2.c_str());

  float bar = (snrEma - 1.0f) / 5.0f;   // map 1..6 => 0..1
  drawBar(0, 34, 128, 10, bar);

  String tail = decodedRaw;
  if (tail.length() > 60) tail = tail.substring(tail.length() - 60);
  u8g2.drawStr(0, 58, tail.c_str());

  u8g2.sendBuffer();
}

static void oledRenderMenu() {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x12_tr);

  u8g2.drawStr(0, 12, "MENU (short=next, hold=select)");
  for (int i = 0; i < 4; i++) {
    int idx = (menuIdx + i) % MI_COUNT;
    String line = String((idx == menuIdx) ? "> " : "  ");
    line += menuItemLabel(idx);

    if (idx == MI_TRAIN)   line += trainingMode ? ":ON" : ":OFF";
    if (idx == MI_EXPAND)  line += expandShorthand ? ":ON" : ":OFF";
    if (idx == MI_LORA)    line += String(":") + loraStatusText();
    if (idx == MI_TONE)    line += " " + String((int)targetToneHz);
    if (idx == MI_SENS)    line += " " + String(sensitivity, 2);
    if (idx == MI_SQUELCH) line += " " + String(squelchSNR, 2);

    u8g2.drawStr(0, 28 + i*9, line.c_str());
  }
  u8g2.sendBuffer();
}

static void oledRenderAdjust(const char* title, const String& value, float bar01) {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x12_tr);
  u8g2.drawStr(0, 12, title);
  u8g2.drawStr(0, 30, value.c_str());
  drawBar(0, 40, 128, 12, bar01);
  u8g2.drawStr(0, 62, "short=inc, hold=back");
  u8g2.sendBuffer();
}

// ===================== QR helpers ===========================
static String wifiQrEscape(const String& s) {
  String out;
  out.reserve(s.length() + 8);
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (c == '\\' || c == ';' || c == ',' || c == ':' || c == '"') out += '\\';
    out += c;
  }
  return out;
}

static String wifiQrPayload(const String& ssid, const String& pass) {
  String p = "WIFI:T:WPA;S:";
  p += wifiQrEscape(ssid);
  p += ";P:";
  p += wifiQrEscape(pass);
  p += ";;";
  return p;
}

#if QR_IMPL_ESP
// ESP32 core QR: esp_qrcode_generate calls cfg.display_func(handle)
// We'll draw into u8g2 inside the callback.
static int g_qr_x0 = 0, g_qr_y0 = 0, g_qr_scale = 2;

static void drawQrToU8g2(esp_qrcode_handle_t qrcode) {
  int qr_size = esp_qrcode_get_size(qrcode);
  if (qr_size <= 0) return;

  // Draw modules
  for (int y = 0; y < qr_size; y++) {
    for (int x = 0; x < qr_size; x++) {
      if (esp_qrcode_get_module(qrcode, x, y)) {
        u8g2.drawBox(g_qr_x0 + x * g_qr_scale, g_qr_y0 + y * g_qr_scale, g_qr_scale, g_qr_scale);
      }
    }
  }
}
#endif

// ----- Layout (no border, QR left, text right) -----
const int pad = 2;

// Give QR a fixed left column. 64px wide works well on 128x64.
const int qrAreaX = 0 + pad;
const int qrAreaY = 0 + pad;
const int qrAreaW = 64 - (pad * 2);
const int qrAreaH = 64 - (pad * 2);

// Text panel to the right
const int textX = 64 + pad;
const int textY = 12;              // first baseline
const int lineH = 12;

static void oledQrJoinScreen() {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x12_tr);

  // Right panel text (info)
  u8g2.drawStr(textX, textY + 0*lineH, "Join WiFi:");
  u8g2.drawStr(textX, textY + 1*lineH, AP_SSID);

  String pw = String("PW: ") + AP_PASS;
  u8g2.drawStr(textX, textY + 2*lineH, pw.c_str());

  IPAddress ip = WiFi.softAPIP();
  String ipt = String("IP: ") + ip.toString();
  u8g2.drawStr(textX, textY + 3*lineH, ipt.c_str());

  u8g2.drawStr(textX, textY + 4*lineH, "hold=back");

#if HAVE_QRCODE_H
  // QR area: left panel (no border)
  String payload = wifiQrPayload(AP_SSID, AP_PASS);

  const int innerX = qrAreaX;
  const int innerY = qrAreaY;
  const int innerW = qrAreaW;
  const int innerH = qrAreaH;

#if QR_IMPL_ESP
  // Force a smaller QR version so modules can be drawn larger (smidge bigger)
  // Version 3 = 29x29 modules -> with a ~60px box we can do scale=2
  esp_qrcode_config_t cfg = ESP_QRCODE_CONFIG_DEFAULT();
  cfg.display_func = drawQrToU8g2;
  cfg.max_qrcode_version = 3;
  cfg.qrcode_ecc_level = ESP_QRCODE_ECC_LOW;

  const int assumed = 29; // version 3 module size
  g_qr_scale = min(innerW, innerH) / assumed;
  if (g_qr_scale < 1) g_qr_scale = 1;

  int drawW = assumed * g_qr_scale;
  int drawH = assumed * g_qr_scale;
  g_qr_x0 = innerX + (innerW - drawW) / 2;
  g_qr_y0 = innerY + (innerH - drawH) / 2;

  esp_err_t ret = esp_qrcode_generate(&cfg, payload.c_str());
  if (ret != ESP_OK) {
    // Keep error text in the right panel so it doesn't stomp the QR area
    u8g2.drawStr(textX, 63, "QR gen failed");
  }

#elif QR_IMPL_RICMOO
  // RicMoo QRCode library
  // Force version 3 so we can scale to 2x in the available box (smidge bigger)
  const uint8_t qrVersion = 2; // (kept as-is)
  const size_t bufSize = qrcode_getBufferSize(qrVersion);
  uint8_t* qrcodeData = (uint8_t*)malloc(bufSize);
  if (qrcodeData) {
    QRCode qrcode;
    qrcode_initText(&qrcode, qrcodeData, qrVersion, ECC_LOW, payload.c_str());

    int qrSize = qrcode.size;
    int scale = min(innerW / qrSize, innerH / qrSize);
    if (scale < 1) scale = 1;

    // If there's room, bump scale up by 1 (no clipping)
    if ((qrSize * (scale + 1) <= innerW) && (qrSize * (scale + 1) <= innerH)) {
      scale++;
    }

    int x0 = innerX + (innerW - (qrSize * scale)) / 2;
    int y0 = innerY + (innerH - (qrSize * scale)) / 2;

    for (int y = 0; y < qrSize; y++) {
      for (int x = 0; x < qrSize; x++) {
        if (qrcode_getModule(&qrcode, x, y)) {
          u8g2.drawBox(x0 + x * scale, y0 + y * scale, scale, scale);
        }
      }
    }

    free(qrcodeData);
  } else {
    u8g2.drawStr(textX, 63, "QR mem fail");
  }
#else
  u8g2.drawStr(textX, 63, "QR lib unsupported");
#endif

#else
  u8g2.drawStr(textX, 63, "qrcode.h missing");
#endif

  u8g2.sendBuffer();
}

static void oledRender() {
  switch (uiScreen) {
    case SCREEN_MAIN:     oledRenderMain(); break;
    case SCREEN_MENU:     oledRenderMenu(); break;
    case SCREEN_ADJ_TONE: {
      float bar = (targetToneHz - 300.0f) / 900.0f;
      oledRenderAdjust("ADJUST TONE", String((int)targetToneHz) + " Hz", bar);
    } break;
    case SCREEN_ADJ_SENS: {
      float bar = (sensitivity - 0.5f) / 1.5f;
      oledRenderAdjust("ADJUST SENS", String(sensitivity, 2), bar);
    } break;
    case SCREEN_ADJ_SQL: {
      float bar = (squelchSNR - 1.0f) / 5.0f;
      oledRenderAdjust("ADJUST SQUELCH", "SNRx " + String(squelchSNR, 2), bar);
    } break;
    case SCREEN_QR: {
      oledQrJoinScreen();
    } break;
  }
}

// ===================== Goertzel =============================
static void computeGoertzelForFreq(float freqHz) {
  float k = 0.5f + ((BLOCK_N * freqHz) / SAMPLE_RATE);
  float w = (2.0f * PI * k) / BLOCK_N;
  goertzel_sine   = sinf(w);
  goertzel_cosine = cosf(w);
  goertzel_coeff  = 2.0f * goertzel_cosine;
}

static float goertzelMagnitude(const int16_t* x, int N) {
  float s_prev = 0.0f, s_prev2 = 0.0f;
  for (int i = 0; i < N; i++) {
    float s = x[i] + goertzel_coeff * s_prev - s_prev2;
    s_prev2 = s_prev;
    s_prev  = s;
  }
  float real = s_prev - s_prev2 * goertzel_cosine;
  float imag = s_prev2 * goertzel_sine;
  return sqrtf(real*real + imag*imag);
}

static TonePick autoFindTone(const int16_t* block, int N) {
  TonePick best{targetToneHz, -1.0f};

  for (float f = 400.0f; f <= 1000.0f; f += 10.0f) {
    computeGoertzelForFreq(f);
    float m = goertzelMagnitude(block, N);
    if (m > best.mag) { best.mag = m; best.freq = f; }
  }

  TonePick fine{best.freq, best.mag};
  for (float f = best.freq - 30.0f; f <= best.freq + 30.0f; f += 2.0f) {
    if (f < 300.0f || f > 1200.0f) continue;
    computeGoertzelForFreq(f);
    float m = goertzelMagnitude(block, N);
    if (m > fine.mag) { fine.mag = m; fine.freq = f; }
  }

  computeGoertzelForFreq(fine.freq);
  return fine;
}

// ===================== Adaptive dot timing ==================
static void pushMarkDuration(float ms) {
  markDurations[markIdx] = ms;
  markIdx = (markIdx + 1) % MARK_HISTORY;
  if (markCount < MARK_HISTORY) markCount++;
}

static float estimateDotFromMarks() {
  if (markCount < 6) return dotMs;

  float tmp[MARK_HISTORY];
  for (int i = 0; i < markCount; i++) tmp[i] = markDurations[i];

  for (int i = 0; i < markCount - 1; i++) {
    int minI = i;
    for (int j = i + 1; j < markCount; j++) if (tmp[j] < tmp[minI]) minI = j;
    float t = tmp[i]; tmp[i] = tmp[minI]; tmp[minI] = t;
  }

  int idx = (int)floorf(0.25f * (markCount - 1));
  float candidate = tmp[idx];

  if (candidate < 20.0f)  candidate = 20.0f;
  if (candidate > 300.0f) candidate = 300.0f;
  return candidate;
}

static void adaptDot(float candidate) {
  dotMs = (1.0f - 0.12f) * dotMs + 0.12f * candidate;
}

// ===================== Output + Expansion hooks =============
static void onDecodedChar(char c) {
  decodedRaw += c;
  if (c != ' ' && c != '\n' && c != '\r') currentWord += c;
  clampBuffers();
}

static void onWordBoundary() {
  if (currentWord.length() == 0) return;
  String out = expandWord(currentWord);
  decodedExpanded += out;
  decodedExpanded += " ";
  currentWord = "";
  clampBuffers();
}

static void flushCurrentSymbol() {
  if (currentSymbol.length() == 0) return;
  char c = decodeMorse(currentSymbol);
  if (c == 0) c = '#';
  currentSymbol = "";
  onDecodedChar(c);
}

static void handleSpace(float spaceMs) {
  float units = spaceMs / dotMs;

  if (units >= 3.0f) {
    flushCurrentSymbol();
  }

  if (units >= 7.0f) {
    flushCurrentSymbol();
    onDecodedChar(' ');
    onWordBoundary();
  }
}

static void handleMark(float markMs) {
  pushMarkDuration(markMs);
  adaptDot(estimateDotFromMarks());

  if (markMs >= (2.0f * dotMs)) currentSymbol += "-";
  else                          currentSymbol += ".";
}

// ===================== PRG Button Event Pump ================
static BtnEvent pollPrgButtonEvent() {
  bool downNow = (digitalRead(PIN_PRG_BTN) == LOW);
  uint32_t now = millis();

  static bool hold1Fired = false;
  BtnEvent ev = BTN_NONE;

  if (downNow && !btnDown) {
    btnDown = true;
    btnDownMs = now;
    panicFired = false;
    hold1Fired = false;
  } else if (downNow && btnDown) {
    uint32_t held = now - btnDownMs;

    if (!panicFired && held >= HOLD_2S_MS) {
      panicFired = true;
      ev = BTN_PANIC;
    } else if (!hold1Fired && held >= HOLD_1S_MS) {
      hold1Fired = true;
      ev = BTN_HOLD1;
    }
  } else if (!downNow && btnDown) {
    btnDown = false;
    if (panicFired || hold1Fired) ev = BTN_NONE;
    else ev = BTN_SHORT;
  }

  return ev;
}

static void uiPanicToMain() {
  uiScreen = SCREEN_MAIN;
  menuIdx = 0;
}

// ===================== Sampling + Detector ===================
static void resetDetectorFloors() {
  noiseFloor = 0.0f;
  signalFloor = 0.0f;
  detectLevel = 0.0f;
  tonePresent = false;
  currentSymbol = "";
  lastTransitionMs = millis();
  snrEma = 1.0f;
}

static void sampleBlock(int16_t* block) {
  uint32_t t0 = micros();
  for (int i = 0; i < BLOCK_N; i++) {
    int v = analogRead(ADC_PIN);
    v -= 2048;
    block[i] = (int16_t)v;

    uint32_t target = t0 + (uint32_t)((i + 1) * (1000000.0f / SAMPLE_RATE));
    while ((int32_t)(micros() - target) < 0) {}
  }
}

static void processBlock() {
  static int16_t block[BLOCK_N];
  sampleBlock(block);

  float mag = goertzelMagnitude(block, BLOCK_N);

  detectLevel = 0.85f * detectLevel + 0.15f * mag;

  if (noiseFloor == 0.0f) noiseFloor = detectLevel;
  if (detectLevel < noiseFloor) noiseFloor = 0.90f * noiseFloor + 0.10f * detectLevel;
  else                          noiseFloor = 0.995f * noiseFloor + 0.005f * detectLevel;

  if (signalFloor == 0.0f) signalFloor = detectLevel;
  if (detectLevel > signalFloor) signalFloor = 0.90f * signalFloor + 0.10f * detectLevel;
  else                           signalFloor = 0.997f * signalFloor + 0.003f * detectLevel;

  float span = signalFloor - noiseFloor;
  if (span < 1.0f) span = 1.0f;

  float onFrac  = 0.45f / sensitivity;
  float offFrac = 0.30f / sensitivity;
  onFrac  = clampf(onFrac,  0.15f, 0.80f);
  offFrac = clampf(offFrac, 0.10f, 0.70f);

  thrOn  = noiseFloor + onFrac  * span;
  thrOff = noiseFloor + offFrac * span;

  float snrNow = (noiseFloor > 0.0f) ? (detectLevel / noiseFloor) : 1.0f;
  if (snrNow < 0.1f) snrNow = 0.1f;
  if (snrNow > 20.0f) snrNow = 20.0f;
  snrEma = 0.90f * snrEma + 0.10f * snrNow;

  bool squelchOpen = (snrEma >= squelchSNR);

  bool newTone = tonePresent;
  if (!squelchOpen) {
    newTone = false;
  } else {
    if (!tonePresent && detectLevel > thrOn)  newTone = true;
    if ( tonePresent && detectLevel < thrOff) newTone = false;
  }

  uint32_t nowMs = millis();

  if (newTone != tonePresent) {
    // PATCH: tone edge transition counts as "input activity" for OLED wake timer
    noteActivity();

    uint32_t dur = nowMs - lastTransitionMs;
    lastTransitionMs = nowMs;

    if (tonePresent) handleMark((float)dur);
    else             handleSpace((float)dur);

    tonePresent = newTone;
  }

  if (!tonePresent) {
    uint32_t silentFor = nowMs - lastTransitionMs;
    if (silentFor > (uint32_t)(7.0f * dotMs * 1.2f)) {
      flushCurrentSymbol();
    }
  }
}

// ===================== Calibration ==========================
static void calibrateNow() {
  Serial.println("[CAL] Listening... send tone/characters now.");

  int16_t block[BLOCK_N];
  TonePick best{targetToneHz, -1.0f};

  for (int tries = 0; tries < 14; tries++) {
    sampleBlock(block);
    TonePick p = autoFindTone(block, BLOCK_N);
    if (p.mag > best.mag) best = p;
    delay(10);
  }

  targetToneHz = best.freq;
  computeGoertzelForFreq(targetToneHz);
  resetDetectorFloors();

  Serial.printf("[CAL] Tone locked: %.1f Hz\n", targetToneHz);
}

// ===================== Web UI ================================
static String htmlPage() {
  return R"HTML(
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Morse Whisperer</title>
<style>
  :root{ --pad:12px; }
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 12px; font-size: 14px; }
  h2 { margin: 6px 0 10px 0; font-size: 18px; }
  .box { border: 1px solid #ddd; padding: var(--pad); border-radius: 14px; margin-bottom: 10px; }
  .row { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
  button { padding: 9px 11px; margin: 6px 6px 0 0; border-radius: 10px; border:1px solid #ccc; background:#f7f7f7; }
  button:active{ transform: translateY(1px); }
  label { display: inline-flex; align-items:center; gap:8px; margin: 6px 12px 0 0; }
  input[type="number"] { width: 90px; padding: 8px; border-radius:10px; border:1px solid #ccc; }
  input[type="range"] { width: min(320px, 90vw); }
  pre { white-space: pre-wrap; word-wrap: break-word; font-size: 12px; line-height: 1.35; margin: 8px 0 0 0; }
  .small { font-size: 12px; color: #666; margin-top: 6px; }
  .k { font-weight: 600; }
  .pill{ display:inline-block; padding:2px 8px; border:1px solid #ddd; border-radius:999px; font-size:12px; }
  @media (max-width: 420px){
    body { margin: 10px; font-size: 13px; }
    h2 { font-size: 17px; }
    pre { font-size: 12px; }
  }
</style>
</head>
<body>
<h2>The Morse Whisperer</h2>

<div class="box">
  <div class="row">
    <div><span class="k">Mode:</span> <span id="mode" class="pill"></span></div>
    <div><span class="k">Tone:</span> <span id="tone"></span> Hz</div>
    <div><span class="k">WPM:</span> <span id="wpm"></span></div>
    <div><span class="k">SNR:</span> <span id="snr"></span></div>
    <div><span class="k">LoRa:</span> <span id="lora" class="pill"></span></div>
  </div>
  <!-- PATCH: keep web UI text consistent with AP_SSID -->
  <div class="small">Wi-Fi AP: "The Morse Whisperer"</div>
</div>

<div class="box">
  <b>RAW</b>
  <pre id="raw"></pre>
</div>

<div class="box">
  <b>EXPANDED</b>
  <pre id="exp"></pre>
</div>

<div class="box">
  <div class="row">
    <button onclick="fetch('/toggleTrain')">Toggle Training</button>
    <button onclick="fetch('/calibrate')">Calibrate</button>
    <button onclick="fetch('/clear')">Clear</button>
    <button onclick="fetch('/toggleLoRa')">LoRa On/Off</button>
  </div>

  <label><input type="checkbox" id="expand" onchange="setExpand()"> Expand shorthand</label>

  <div class="row">
    <label>Tone Hz: <input type="number" id="toneSet" min="300" max="1200"></label>
    <button onclick="setTone()">Set</button>
  </div>

  <div style="margin-top:8px">
    <div><span class="k">Sensitivity:</span> <span id="sensv"></span></div>
    <input type="range" id="sens" min="0.5" max="2.0" step="0.05" oninput="setSensLive()">
  </div>

  <div style="margin-top:8px">
    <div><span class="k">Squelch (SNRx):</span> <span id="sqlv"></span></div>
    <input type="range" id="sql" min="1.0" max="6.0" step="0.05" oninput="setSqlLive()">
  </div>
</div>

<script>
async function refresh(){
  const r = await fetch('/status');
  const j = await r.json();

  mode.textContent = j.training ? 'TRAIN' : 'RX';
  tone.textContent = j.tone.toFixed(1);
  wpm.textContent  = j.wpm.toFixed(1);
  snr.textContent  = j.snr.toFixed(2);

  raw.textContent  = j.raw;
  exp.textContent  = j.expanded;

  expand.checked   = j.expand;
  toneSet.value    = Math.round(j.tone);

  sens.value       = j.sens.toFixed(2);
  sensv.textContent = j.sens.toFixed(2);

  sql.value        = j.sql.toFixed(2);
  sqlv.textContent = j.sql.toFixed(2);

  lora.textContent = j.lora;
}
async function setExpand(){
  await fetch('/setExpand?on='+(expand.checked?1:0));
}
async function setTone(){
  await fetch('/setTone?hz='+encodeURIComponent(toneSet.value));
}
async function setSensLive(){
  sensv.textContent = Number(sens.value).toFixed(2);
  await fetch('/setSens?v='+encodeURIComponent(sens.value));
}
async function setSqlLive(){
  sqlv.textContent = Number(sql.value).toFixed(2);
  await fetch('/setSql?v='+encodeURIComponent(sql.value));
}
setInterval(refresh, 500);
refresh();
</script>
</body></html>
)HTML";
}

static void webBegin() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);

  server.on("/", [](){
    server.send(200, "text/html", htmlPage());
  });

  server.on("/status", [](){
    String json = "{";
    json += "\"training\":" + String(trainingMode ? "true" : "false") + ",";
    json += "\"tone\":" + String(targetToneHz, 1) + ",";
    json += "\"wpm\":" + String(wpmEstimate(), 1) + ",";
    json += "\"snr\":" + String(snrEma, 2) + ",";
    json += "\"expand\":" + String(expandShorthand ? "true" : "false") + ",";
    json += "\"sens\":" + String(sensitivity, 2) + ",";
    json += "\"sql\":" + String(squelchSNR, 2) + ",";
#if HAVE_RADIOLIB
    json += "\"lora\":\"" + String(loraEnabled ? "ON" : "OFF") + "\",";
#else
    json += "\"lora\":\"N/A\",";
#endif
    json += "\"raw\":\"" + jsonEscape(decodedRaw) + "\",";
    json += "\"expanded\":\"" + jsonEscape(decodedExpanded) + "\"";
    json += "}";
    server.send(200, "application/json", json);
  });

  server.on("/toggleTrain", [](){
    trainingMode = !trainingMode;
    if (trainingMode) calibrateNow();
    server.send(200, "text/plain", "OK");
  });

  server.on("/calibrate", [](){
    calibrateNow();
    server.send(200, "text/plain", "OK");
  });

  server.on("/clear", [](){
    decodedRaw = "";
    decodedExpanded = "";
    currentWord = "";
    currentSymbol = "";
    server.send(200, "text/plain", "OK");
  });

  server.on("/setExpand", [](){
    expandShorthand = (server.arg("on") == "1");
    server.send(200, "text/plain", "OK");
  });

  server.on("/setTone", [](){
    float hz = server.arg("hz").toFloat();
    hz = clampf(hz, 300.0f, 1200.0f);
    targetToneHz = hz;
    computeGoertzelForFreq(targetToneHz);
    resetDetectorFloors();
    server.send(200, "text/plain", "OK");
  });

  server.on("/setSens", [](){
    float v = server.arg("v").toFloat();
    v = clampf(v, 0.5f, 2.0f);
    sensitivity = v;
    server.send(200, "text/plain", "OK");
  });

  server.on("/setSql", [](){
    float v = server.arg("v").toFloat();
    v = clampf(v, 1.0f, 6.0f);
    squelchSNR = v;
    server.send(200, "text/plain", "OK");
  });

  server.on("/toggleLoRa", [](){
    setLoRaEnabled(!loraEnabled);
    server.send(200, "text/plain", "OK");
  });

  server.begin();

  Serial.print("[WEB] AP SSID: ");
  Serial.println(AP_SSID);
  Serial.print("[WEB] AP IP  : ");
  Serial.println(WiFi.softAPIP());
}

// ===================== Menu Actions ==========================
static void menuSelect(MenuItem mi) {
  switch (mi) {
    case MI_TRAIN:
      trainingMode = !trainingMode;
      if (trainingMode) calibrateNow();
      break;

    case MI_EXPAND:
      expandShorthand = !expandShorthand;
      break;

    case MI_CALIBRATE:
      calibrateNow();
      break;

    case MI_TONE:
      uiScreen = SCREEN_ADJ_TONE;
      break;

    case MI_SENS:
      uiScreen = SCREEN_ADJ_SENS;
      break;

    case MI_SQUELCH:
      uiScreen = SCREEN_ADJ_SQL;
      break;

    case MI_LORA:
      setLoRaEnabled(!loraEnabled);
      break;

    case MI_QR:
      uiScreen = SCREEN_QR;
      qrEnterMs = millis();
      break;

    case MI_CLEAR:
      decodedRaw = "";
      decodedExpanded = "";
      currentWord = "";
      currentSymbol = "";
      break;

    case MI_EXIT:
      uiScreen = SCREEN_MAIN;
      break;

    default:
      break;
  }
}

// ===================== Power / Init ==========================
static void vextOn() {
  pinMode(PIN_VEXT_CTRL, OUTPUT);
  digitalWrite(PIN_VEXT_CTRL, VEXT_ON_LEVEL);
}

// ===================== Setup / Loop ==========================
void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(PIN_PRG_BTN, INPUT_PULLUP);

  analogReadResolution(12);

  vextOn();
  delay(50);

  u8g2.begin();
  u8g2.setPowerSave(0); // PATCH: ensure OLED is awake before splash
  oledSplash();
  delay(5000);

  // PATCH: start OLED idle timer after splash
  lastActivityMs = millis();
  oledSleeping = false;

  computeGoertzelForFreq(targetToneHz);
  resetDetectorFloors();

  setLoRaEnabled(false);

  webBegin();

  Serial.println();
  Serial.println("=====================================");
  Serial.println(PROJECT_NAME);
  Serial.println(PROJECT_TAG);
  Serial.println(VERSION_STR);
  Serial.println("PRG hold ~1s: Menu | hold ~2s: Panic to main");
  Serial.println("=====================================");
}

void loop() {
  processBlock();

  BtnEvent ev = pollPrgButtonEvent();

  // PATCH: any button event counts as input activity (wakes OLED)
  if (ev != BTN_NONE) noteActivity();

  if (ev == BTN_PANIC) {
    uiPanicToMain();
  } else if (uiScreen == SCREEN_MAIN) {
    if (ev == BTN_HOLD1) {
      uiScreen = SCREEN_MENU;
      menuIdx = 0;
    }
  } else if (uiScreen == SCREEN_MENU) {
    if (ev == BTN_SHORT) {
      menuIdx = (menuIdx + 1) % MI_COUNT;
    } else if (ev == BTN_HOLD1) {
      menuSelect((MenuItem)menuIdx);
    }
  } else if (uiScreen == SCREEN_QR) {
    if (ev == BTN_HOLD1) {
      uiScreen = SCREEN_MENU;
    }
    if (millis() - qrEnterMs > 20000UL) {
      uiScreen = SCREEN_MENU;
    }
  } else {
    if (ev == BTN_HOLD1) {
      uiScreen = SCREEN_MENU;
    } else if (ev == BTN_SHORT) {
      if (uiScreen == SCREEN_ADJ_TONE) {
        targetToneHz += 10.0f;
        if (targetToneHz > 1200.0f) targetToneHz = 300.0f;
        computeGoertzelForFreq(targetToneHz);
        resetDetectorFloors();
      } else if (uiScreen == SCREEN_ADJ_SENS) {
        sensitivity += 0.05f;
        if (sensitivity > 2.0f) sensitivity = 0.5f;
      } else if (uiScreen == SCREEN_ADJ_SQL) {
        squelchSNR += 0.05f;
        if (squelchSNR > 6.0f) squelchSNR = 1.0f;
      }
    }
  }

  server.handleClient();

  // PATCH: enforce OLED sleep after inactivity
  oledSleepCheck();

  static uint32_t lastOled = 0;
  if (!oledSleeping && (millis() - lastOled > 120)) {
    lastOled = millis();
    oledRender();
  }
}
