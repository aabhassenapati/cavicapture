import configparser
import time
import datetime
import sys
import os
import getopt
import RPi.GPIO as GPIO
from picamera2 import Picamera2
import cv2
import sqlite3
import subprocess

def main():
    generate_preview = False
    config_path = ""
    print(f"Received config path: {config_path}")
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:p", ["config=", "preview"])
    except getopt.GetoptError:
        print("Usage: cavicapture.py --config <path/to/config.ini> --preview")
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == "--config":
            config_path = arg
        elif opt == "--preview":
            generate_preview = True
    
    if not config_path:
        print("Error: Config file path is required.")
        sys.exit(2)
    
    cavi_capture = CaviCapture(config_path)
    if generate_preview:
        cavi_capture.generate_preview()
    else:
        cavi_capture.start()

class CaviCapture:
    def __init__(self, config_file):
        self.config_file = config_file
        self.current_capture = False
        self.capture_timestamp = ""
        self.load_config()
        self.setup_gpio()
        self.create_directories()
        self.log_file = os.path.join(self.sequence_path, "log.txt")
        self.setup_db()

    def load_config(self):
        config = configparser.ConfigParser()
        config.read(self.config_file)
        
        print(f"Reading from config file: {self.config_file}")
        
        self.camera_ISO = config.getint('camera', 'ISO')
        self.camera_shutter_speed = config.get('camera', 'shutter_speed')
        self.capture_duration = config.getfloat('capture', 'duration')
        self.capture_interval = config.getint('capture', 'interval')
        self.output_dir = config.get('capture', 'output_dir')
        self.capture_sequence_name = config.get('capture', 'sequence_name')
        self.resolution = config.get('capture', 'resolution')
        self.verbose = config.getboolean('capture', 'verbose')
        self.crop_enabled = config.getboolean('capture', 'crop_enabled')
        self.crop = tuple(map(float, config.get('capture', 'crop').split(',')))
        self.pi_GPIO_light_channel = config.getint('pi', 'GPIO_light_channel')

    def generate_preview(self):
        self.setup_camera()
        self.log_info("Generating preview")
        self.lights(True)
        self.camera.capture_file(os.path.join(self.sequence_path, "preview.jpg"))
        self.lights(False)
        
    def start(self):
        self.setup_camera()
        self.log_info("Starting capture sequence")
        capture_time_end = time.time() + (self.capture_duration * 3600)
        
        try:
            while time.time() < capture_time_end:
                self.capture_timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
                output_filename = f"{self.capture_timestamp}.jpg"
                self.log_info(f"Capturing {output_filename}")
                self.lights(True)
                self.capture(output_filename)
                self.lights(False)
                time.sleep(self.capture_interval)
        except KeyboardInterrupt:
            self.log_info("Sequence terminated by user.")
        finally:
            GPIO.cleanup()
            self.db_conn.close()

    def capture(self, output_filename):
        filepath = os.path.join(self.sequence_path, output_filename)
        self.camera.capture_file(filepath)
        
        if self.crop_enabled and len(self.crop) == 4:
            img = cv2.imread(filepath)
            h, w = img.shape[:2]
            x1, y1, x2, y2 = [int(v * w if i % 2 == 0 else v * h) for i, v in enumerate(self.crop)]
            cv2.imwrite(filepath, img[y1:y2, x1:x2])
        
        self.db_conn.execute("INSERT INTO captures (filename, timestamp, skip, processing, processed) VALUES (?, ?, 0, 0, 0)", (output_filename, self.capture_timestamp))
        self.db_conn.commit()

    def setup_camera(self):
        self.camera = Picamera2()
        self.camera.set_controls({"ExposureTime": int(self.camera_shutter_speed) if self.camera_shutter_speed.isdigit() else 10000, "AnalogueGain": 1.0})
        res_map = {"Max": (4608, 2592), "Large": (3280, 2464), "Medium": (1920, 1080), "Small": (640, 480)}
        self.camera.configure(self.camera.create_still_configuration(main={'size': res_map.get(self.resolution, (640, 480))}))
        self.camera.start()

    def setup_gpio(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pi_GPIO_light_channel, GPIO.OUT)

    def create_directories(self):
        os.makedirs(self.output_dir, exist_ok=True)
        self.sequence_path = os.path.join(self.output_dir, self.capture_sequence_name)
        os.makedirs(self.sequence_path, exist_ok=True)

    def setup_db(self):
        self.db_conn = sqlite3.connect(os.path.join(self.sequence_path, 'capture.db'))
        self.db_conn.execute('''CREATE TABLE IF NOT EXISTS captures
                                (id INTEGER PRIMARY KEY, filename TEXT, timestamp TEXT, skip INTEGER, processed INTEGER, processing INTEGER, area REAL)''')
        self.log_info("Database initialized")

    def lights(self, active):
        GPIO.output(self.pi_GPIO_light_channel, active)
        if active:
            time.sleep(3)
    
    def log_info(self, entry):
        print(f"INFO: {entry}")
        with open(self.log_file, 'a') as log:
            log.write(f"{entry}\n")

if __name__ == '__main__':
    main()
