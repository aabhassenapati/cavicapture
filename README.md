# cavicapture

*Required python modules for script*:

```
sudo apt-get install python-scipy
sudo apt-get install python-opencv
sudo apt-get install python-matplotlib
```

Increase GPU memory (otherwise picamera won’t be able to do high resolution image capture)

`sudo raspi-config`

Change "Memory Split" under "Advanced Options" to 256 (i.e. 256mb)
