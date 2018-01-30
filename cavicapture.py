#!/usr/bin/python

import RPi.GPIO as GPIO
import picamera
import time, datetime
import sys
import getopt

inst = "cavicapture.py -i <interval,sec> -d <duration,sec> -s <shutterspeed,ms> -I <iso>"

shutter_speed = 0
ISO = 0
setup_mode = False

try:
    opts, args = getopt.getopt(sys.argv[1:], "hi:d:s:S:I", ["interval=","duration=","shutterspeed=","setup", "ISO="])
except getopt.GetoptError:
    sys.exit(2)
for opt, arg in opts:
    if opt == '-h':
        sys.exit()
    elif opt in ("-i", "--interval"):
        interval = int(arg)
    elif opt in ("-d", "--duration"):
        duration = int(arg)
    elif opt in ("-S", "--setup"):
        setup_mode = True
    elif opt in ("-s", "--shutterspeed"):
        shutter_speed = int(arg)
    elif opt in ("-I", "--ISO"):
        ISO = int(arg)


# GPIO setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(7, GPIO.OUT)

# Turn the light on 
GPIO.output(7, True)

# Get camera
print("\nConfiguring camera...")
camera = picamera.PiCamera(resolution=(2592, 1944), framerate=15)

max_intensity = camera.resolution.height * camera.resolution.width * 255

if ISO:
    camera.iso = ISO
else:
    camera.iso = 100

time.sleep(2)

print("Auto (current) shutter speed: %d" % camera.exposure_speed)

if shutter_speed:
    print("Setting shutter speed to: ~%d" % shutter_speed)
    camera_shutter_speed = shutter_speed
else:
    camera_shutter_speed = camera.exposure_speed

camera.shutter_speed = camera_shutter_speed
camera.exposure_mode = 'off'
current_gains = camera.awb_gains
camera.awb_mode = 'off'
camera.awb_gains = current_gains

# Start configuration
if setup_mode:
    raw_input("\n\nPress ENTER to show preview. Press ENTER when finished.")
else:
    raw_input("\n\nPress ENTER to start preparing sample (align, focus etc). Preview window will show. Press ENTER when finished (or CTRL-C to cancel).")

try:
    camera.start_preview()
    raw_input("Press ENTER to continue (or CTRL-C to cancel)...")
    camera.stop_preview()
except KeyboardInterrupt:
    camera.stop_preview()
    GPIO.output(7, False)
    sys.exit(2)

if setup_mode:
    GPIO.output(7, False)
    sys.exit(2)

# Save capture parameters to file
params = open('params.txt', 'a');
params.write('start: '+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'\n');
params.write('interval (s): %d\n' % interval);
params.write('duration (s): %d\n' % duration);
params.write('shutter speed (ms): %d\n' % camera.exposure_speed);
params.write('\n\n');
params.close();

print("Configuration complete. Running sequence.")

# Main loop
seq_end = time.time() + duration

try:
    while time.time() < seq_end:

        filename = datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + ".png"

        # Turn LEDs on
        GPIO.output(7, True)
        time.sleep(2)

        # Fix the shutter speed
        camera.shutter_speed = camera_shutter_speed

        print("Capturing " + filename)
        # Take picture
        camera.capture(filename, 'png')
        time.sleep(3)
        
        # Turn LEDs off
        GPIO.output(7, False)

        # Wait interval
        time.sleep(interval)

    print("Sequence completed.")

except KeyboardInterrupt:
    GPIO.output(7, False)
    print("Sequence terminated by user.")
except IOError as e:
    GPIO.output(7, False)
    print "I/O error({0}): {1}".format(e.errno, e.strerror)
except:
    GPIO.output(7, False)
    print "Error:", sys.exc_info()[0]
