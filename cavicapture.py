#!/usr/bin/python

import RPi.GPIO as GPIO
import picamera
import time, datetime
import sys
import getopt
import cv2
import numpy as np
import matplotlib.pyplot as plt

inst = "cavicapture.py -i <interval,sec> -d <duration,sec> -s <shutterspeed,ms> -I <iso>"

shutter_speed = 0
ISO = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], "hi:d:s:I", ["interval=","duration=","shutterspeed=","ISO="])
except getopt.GetoptError:
    sys.exit(2)
for opt, arg in opts:
    if opt == '-h':
        sys.exit()
    elif opt in ("-i", "--interval"):
        interval = int(arg)
    elif opt in ("-d", "--duration"):
        duration = int(arg)
    elif opt in ("-s", "--shutterspeed"):
        shutter_speed = int(arg)
    elif opt in ("-I", "--ISO"):
        ISO = int(arg)


# Get camera
camera = picamera.PiCamera()

max_intensity = camera.resolution.height * camera.resolution.width * 255

if ISO:
    camera.ISO = ISO
else:
    camera.ISO = 100

if shutter_speed:
    camera.shutter_speed = shutter_speed

# GPIO setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(7, GPIO.OUT)

# Start configuration
raw_input("Press ENTER to start preparing sample (align, focus etc). Preview window will show. Press ENTER when finished (or CTRL-C to cancel).")

try:
    GPIO.output(7, True)
    camera.start_preview()
    raw_input("Press ENTER to continue (or CTRL-C to cancel)...")
    camera.stop_preview()
except KeyboardInterrupt:
    camera.stop_preview()
    GPIO.output(7, False)
    sys.exit(2)

print("Configuring camera...")

# Set the camera to full resolution (ensure that the memory split allocation has been increased to 256mb - see README)
camera.resolution = (2592, 1944)
camera.framerate = 15

# Basic settings
camera.color_effects = (128,128) # black and white

# Wait for automatic gain control to settle
time.sleep(2)

# Set the fixed values to automatic values if no shutter speed provided
if not shutter_speed:
    camera.shutter_speed = camera.exposure_speed
    camera.exposure_mode = 'off'

# Get the current automatically determined gains before we turn
# gains off..
current_gains = camera.awb_gains
camera.awb_mode = 'off'
camera.awb_gains = current_gains

print("Configuration complete. Running sequence.")

last_file = ''
last_diff_sum = 0
max_diff = 0
image_n = 1

# Init plot
plt.axis([0, 25, 0, 1])
plt.ion()

# Main loop
seq_end = time.time() + duration

try:
    while time.time() < seq_end:

        filename = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + ".png"
        print("Capturing " + filename)

        # Turn LEDs on
        GPIO.output(7, True)
        time.sleep(3)

        # Take picture
        # camera.start_preview()
        camera.capture(filename, 'png')
        time.sleep(3)
        # camera.stop_preview()

        # Turn LEDs off
        GPIO.output(7, False)

        # calculate image difference
        if last_file:
            img_1 = cv2.imread(last_file)
            img_2 = cv2.imread(filename)
            diff = cv2.subtract(img_2, img_1)

            diff_sum = diff.sum()
            max_diff = max((max_diff, diff_sum))

            cv2.imwrite("diff_" + filename, diff)

            plt.scatter(image_n, diff_sum)

            plt.ylim((0, max_diff + (max_diff * 0.1)))

            if image_n > 20:
                plt.xlim((0, image_n + 5))

            plt.pause(0.05)

            print("Diff -> sum pixel intensities: " + str(diff_sum))

            last_diff_sum = diff_sum

        last_file = filename

        # Wait interval
        time.sleep(interval)
        image_n += 1

except:
    print "Error:", sys.exc_info()[0]
    GPIO.output(7, False)

plt.savefig('intensities.png')
print("Sequence complete.")
