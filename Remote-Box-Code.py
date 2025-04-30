import time
import board
import digitalio
import pwmio
import audiopwmio
from audiocore import WaveFile
import neopixel
import wifi
import socketpool
import ssl
import os

import adafruit_motor.servo
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT

# ---- Load credentials from settings.toml ----
aio_username = os.getenv("ADAFRUIT_AIO_USERNAME").strip()
aio_key = os.getenv("ADAFRUIT_AIO_KEY").strip()
feed_key = "button-press"

# ---- Setup switch input ----
switch_pin = board.GP14
switch = digitalio.DigitalInOut(switch_pin)
switch.direction = digitalio.Direction.INPUT
switch.pull = digitalio.Pull.UP

# ---- Setup Servo output ----
servo_pwm = pwmio.PWMOut(board.GP15, duty_cycle=0, frequency=50)
servo = adafruit_motor.servo.Servo(servo_pwm)
home_angle = 110
target_angle = 58
servo.angle = home_angle

# ---- Setup Audio output ----
audio = audiopwmio.PWMAudioOut(board.GP0)

# ---- Setup Neopixels ----
num_pixels = 30
pixels = neopixel.NeoPixel(board.GP1, num_pixels, brightness=0.5, auto_write=False)
pixels.fill((0, 0, 0))
pixels.show()

# ---- Setup Wi-Fi and MQTT ----
pool = socketpool.SocketPool(wifi.radio)
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=aio_username,
    password=aio_key,
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

aio_client = IO_MQTT(mqtt_client)

# ---- Functions ----

def move_servo_once():
    print("Starting servo movement...")
    servo.angle = target_angle
    time.sleep(0.5)
    servo.angle = home_angle
    print("Servo returned home.")

def play_sound_and_pulse_lights(filename):
    move_servo_once()  # Move servo first

    for play_count in range(3):  # Play sound 3 times
        print(f"Play #{play_count + 1} starting...")

        with open(filename, "rb") as wave_file:
            wave = WaveFile(wave_file)
            audio.play(wave)

            while audio.playing:
                # While sound is playing, pulse lights
                pixels.fill((255, 0, 0))  # Red ON
                pixels.show()
                time.sleep(0.2)
                pixels.fill((0, 0, 0))    # Lights OFF
                pixels.show()
                time.sleep(0.2)

# ---- MQTT callbacks ----
def connect(mqtt_client, userdata, flags, rc):
    print("Connected to Adafruit IO!")
    aio_client.subscribe(feed_key)

def message(client, feed_id, payload):
    print(f"Received message on {feed_id}: {payload}")
    if payload == "pressed":
        play_sound_and_pulse_lights("Brewing.wav")

mqtt_client.on_connect = connect
aio_client.on_message = message

# ---- Connect to Adafruit IO ----
aio_client.connect()

# ---- Main loop ----
last_switch = switch.value

while True:
    current = switch.value
    if last_switch and not current:
        print("Local switch pressed, publishing and activating...")
        play_sound_and_pulse_lights("Brewing.wav")

    last_switch = current
    aio_client.loop()
    time.sleep(0.05)  # debounce