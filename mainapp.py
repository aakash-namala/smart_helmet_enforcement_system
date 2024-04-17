from flask import Flask, render_template, Response
import cv2
from ultralytics import YOLO
from picamera2 import Picamera2
from rpi_lcd import LCD
import RPi.GPIO as GPIO
from time import sleep
import time
import subprocess

def check_wifi_connection():
    try:
        result = subprocess.run(['iwconfig'], capture_output=True, text=True)
        if 'ESSID' in result.stdout:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking WiFi connection: {e}")
        return False

def get_ip_address():
    # Get the IP address of wlan0 interface
    try:
        ip_address = subprocess.check_output(['hostname', '-I']).decode().strip()
        return ip_address
    except subprocess.CalledProcessError:
        return None
    
Red_led = 25
Green_led = 10
Motor = 24
But = 18
Buz = 23

detectedName = ''
status = 0
tim = 0
d = 0

GPIO.setwarnings(False)
lcd = LCD()
GPIO.setmode(GPIO.BCM)

GPIO.setup(Red_led, GPIO.OUT)
GPIO.setup(Green_led, GPIO.OUT)
GPIO.setup(Motor, GPIO.OUT)
GPIO.setup(But, GPIO.IN)
GPIO.setup(Buz, GPIO.OUT)
model = YOLO(r'best.pt')

lcd.text('Smart Bike', 1)
lcd.text("Connecting...    ", 2)
while 1:
    if check_wifi_connection():
        break
lcd.text("Fetching IP  ......", 2)
sleep(2)
ip = get_ip_address()
lcd.text(ip, 2)

picam2 = Picamera2()
picam2.preview_configuration.main.size = (640,480)
picam2.preview_configuration.main.format = "RGB888"
picam2.preview_configuration.align()
picam2.configure("preview")
picam2.start()

def detect(image):
    results = model(image,verbose=False)[0]
    Count = len(results)
    annotated_frame = results.plot()
    class_names = ''
    if Count > 0:
        class_names = [results.names[int(class_id)] for class_id in results.boxes.cls][0]
    return annotated_frame,class_names

app = Flask(__name__)
def gen_frames():
    global detectedName
    global status
    global tim
    global d
    global picam2
    while True:
        frame= picam2.capture_array()
        but = GPIO.input(But)
        frame,detectedName = detect(frame)
        if but == 1 and detectedName == 'helmet':
            GPIO.output(Buz, GPIO.HIGH)
            GPIO.output(Red_led, GPIO.LOW)
            GPIO.output(Green_led, GPIO.HIGH)
            GPIO.output(Motor, GPIO.HIGH)
            sleep(0.2)
            GPIO.output(Buz, GPIO.LOW)
            lcd.text('Bike started   ', 2)
            sleep(0.5)
            status = 1
        else:
            if status == 1 and but == 1:
                GPIO.output(Red_led, GPIO.LOW)
                GPIO.output(Green_led, GPIO.LOW)
                status = 0
                GPIO.output(Motor, GPIO.LOW)
                lcd.text(f'                  ', 2)
                d = 0
        if status == 1 and detectedName == 'head' and d ==0:
            GPIO.output(Red_led, GPIO.HIGH)
            GPIO.output(Green_led, GPIO.LOW)
            tim = time.time()
            d =1
            sleep(0.2)
            GPIO.output(Buz, GPIO.LOW)
        if status == 1 and detectedName == 'helmet':
            d = 0
            GPIO.output(Red_led, GPIO.LOW)
            GPIO.output(Green_led, GPIO.HIGH)
            lcd.text(f'                  ', 2)
        if d == 1:
            l_time = int(time.time() - tim)
            #print(l_time)
            lcd.text('Time : '+str(10 - l_time), 2)
            if l_time > 10:
                status = 0
                d = 0
                GPIO.output(Red_led, GPIO.LOW)
                GPIO.output(Green_led, GPIO.LOW)
                GPIO.output(Motor, GPIO.LOW)
                lcd.text('Bike Stoped   ', 2)
                GPIO.output(Buz, GPIO.HIGH)
                sleep(0.5)
                lcd.text(f'                 ', 2)
                GPIO.output(Buz, GPIO.LOW)
        
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(debug=False,host='0.0.0.0')
