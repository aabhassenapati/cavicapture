# Cavicapture 2.0

Cavicapture 2.0 is a significant update that includes:

* Automated image processing using new 'Caviprocess' script.
* New approach to configuring settings for image capture and processing.

# Usage

Image capture and image processing settings are stored in a INI configuration file (see example_config.ini). Settings are updated by manually editing this file using a text editor. 

Cavicapture is run from the console. 

To initiate image capture, the location of the INI configuration is passed to the cavicapture.py script using the '--config' option:

```
sudo python cavicapture.py --config /home/pi/cavicapture/example_config.ini
```

A preview can be generated - a single image capture using the INI settings - by passing the '--preview' option. This will generate a file in the output directory called 'preview.png'.

```
sudo python cavicapture.py --config /home/pi/cavicapture/example_config.ini --preview
```

To initiate image processing, the same INI configuration file is passed to the new caviprocess.py script in the same way:

```
sudo python caviprocess.py --config /home/pi/cavicapture/example_config.ini
```

Image capture and image processing can be run concurrently or independently. When caviprocess is activated it processes any files that are currently available and then waits for new files as they become available. The intention here was to provide the greatest flexibility - if you only want to capture images then you can (and you never run caviprocess), but if you want to process the images then you can do that while the images are being captured or at any time after the sequence has completed.

Captured and processed images are saved in the output directory specified in the config file. Results from image processing are saved in a SQLite database in the root of the output directory. There are a number of SQLite clients available for accessing the data e.g. https://sqlitebrowser.org/ works for both Mac and Windows. 

Cavicapture v2 was built to run from the command line or to be integrated into other software. [OpenSourceOV/caviconsole](https://github.com/OpenSourceOV/caviconsole.git) is a GUI built on top of cavicapture v2.

# Configuration

See example_config.ini for an example of the configuration file. Settings are as follows:

Section | Setting | Description
------------ | ------------ | -------------
camera | ISO | Camera ISO
camera | shutter_speed | Camera shutterspeed
capture | duration | Total run time in hours for image capture
capture | interval | Time in seconds between captures
capture | output_dir | Output directory for sequence folders
capture | sequence_name | Folder name within the output directory for sequence images and settings
capture | verbose | Capturing verbose logging On/Off (keep On)
capture | resolution | Image size: Max=2592x1944, Large=1920x1080, Medium=1296x972, Small=640x480
capture | crop | Crop images to region. x1,y1,x2,y2. Values represent % of image dimension size
capture | crop_enabled | Crop On/Off
process | processor | Location of caviprocess script
process | intermediates_enabled | If enabled ('On') caviprocess will save a copy of the output images at each stage of processing in a sub-folder of the sequence directory. Useful for debugging.
process | outlier_removal_enabled | Outlier removal On/Off
process | filtering_enabled | Filtering On/Off
process | thresholding_enabled | Thresholding On/Off
process | difference_enabled | Difference On/Off
process | roi_enabled | Whether to limit difference counts to a portion of the image (On/Off)
process | roi | Limit difference counts to region x1,y1,x2,y2. Values are % of image dimension size
process | verbose | Processing verbose logging On/Off (keep On)
process | filter_threshold | Filtering threshold value
pi | GPIO_light_channel | Raspberry Pi GPIO channel connected to the light

## Image Processing

Images are processed in sequential pairs using a six-step procedure:

1. Images are converted to 8-bit i.e. each pixel has a grayscale value from 0 (black) to 255 (white)
2. Pixels at corresponding positions in each pair of images are subtracted e.g. pixel at column 1, row 1 of image 1 is subtracted from the pixel value at column 1, row 1 of image 2 then pixel at column 2, row 1 of image 1 is subtracted from the pixel value at column 2, row 1 of image 2, and so on. This results in a new image of differences where pixel values > 0 indicate a difference in pixel values at that position. So, if two images are identical all the pixels in the difference image would be zero. The remainder of the procedure runs on the difference image.
3. Electrical noise results in small differences between the two images that are unrelated to 'real' differences. Most of these differences are small and result in pixels varying by < 7. Embolism events tend to result in pixel differences greater than 7 but this depends on the species, the sample preparation, the lighting etc. In most cases simply removing all pixels with a value < 7 can remove most of the noise, leaving a strong enough signal of the 'real' differences. Trial and error determines the best filtering threshold. 
4. Outlier pixels are removed at a radius of 3 pixels. This means that for every pixel we compare the values of the surrouding pixels up to a radius of 3 pixels and if the middle pixel value is more than the median value of the surrounding values then we set the middle pixel to zero. Noisy pixels are randomly distributed and most of them will be single non-zero pixels with zero-value pixels surrounding them. Outlier removal very effectively removes these 'lone' noisy pixels.
5. Thresholding - all non-zero pixels are set to 255 (white). This step is only required to make it easier to see the differences between images. Without thresholding the image differences look black because the actual pixel values are very small.
6. All non-zero values are counted per image to give a 'Difference total' that represents the total area between the two images that are different.

By turning 'intermediates_enabled' to 'On' in the configuration file you can see a saved version of the processed images at each of these stages of processing. Intermediates are saved in a sub folder of the sequence directory, one set of intermediates for each image pair. Remember - the images differences are very small, so it will appear that all of the intermediate images, except for the final thresholded image, are black. The images should be opened in ImageJ or equivalent for analysis of pixel values (mostly by using the thresholding tool).

# Installation

To setup the Raspberry Pi, follow the instructions for Version 2 at [OpenSourceOV/raspberry-pi-setup](https://github.com/OpenSourceOV/raspberry-pi-setup.git).

These instructions assume you are using the latest version of the Raspbian operating system (Raspbian Stretch v4.4 at the time of writing). If you are not intending on using the caviconsole GUI then older versions of Raspbian should be fine, however the caviconsole GUI requires at least v4.4.

From the console:

```
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install python-opencv -y
cd ~/
git clone https://github.com/OpenSourceOV/cavicapture.git
cd cavicapture && git checkout 2.0
```

## Caviconsole integration

Caviconsole is a GUI (graphical user interface) for editing the configuration file and controlling image capture and processing. See the [OpenSourceOV/caviconsole](https://github.com/OpenSourceOV/caviconsole.git) repository for more information and installation.

## Notes

* If you are installing from new then follow the instructions for Version 2 at [OpenSourceOV/raspberry-pi-setup](https://github.com/OpenSourceOV/raspberry-pi-setup.git) to setup the Raspberry Pi first before installing Cavicapture.
