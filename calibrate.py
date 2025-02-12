import configparser
import sqlite3
import sys
import os
import getopt
import time
import datetime
import glob
import numpy as np
import matplotlib.pyplot as plt
from shutil import copyfile
from cavicapture import CaviCapture
from process import CaviProcess


def main():
    config_path = "./config.ini"
    try:
        opts, args = getopt.getopt(sys.argv[1:], "c", ["config="])
    except getopt.GetoptError:
        print("Argument error")
        sys.exit(2)
    for opt, arg in opts:
        if opt == "--config":
            config_path = arg

    calibrator = CaviCalibrate(config_path)
    calibrator.init_calibration()


class CaviCalibrate:
    def __init__(self, config_path):
        self.output_dir = os.path.join("./calibration", datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
        os.makedirs(self.output_dir, exist_ok=True)

        self.cavi_capture = CaviCapture(config_path)
        self.cavi_capture.log_file = os.path.join(self.output_dir, "capture.log.txt")
        self.cavi_capture.get_ini_config()
        self.cavi_capture.setup_gpio()
        self.cavi_capture.setup_camera()

        self.cavi_process = CaviProcess(self.output_dir)
        self.cavi_process.log_file = os.path.join(self.output_dir, "process.log.txt")

    def init_calibration(self):
        files = []
        self.cavi_capture.lights(True)
        time.sleep(3)
        for i in range(1, 5):
            files.append(self.capture_image(os.path.join(self.output_dir, f"image_{i}.png")))
        self.cavi_capture.lights(False)
        self.process_files(files)

    def process_files(self, files):
        img_group_1_diff = self.cavi_process.subtract_images(files[0], files[1])
        self.cavi_process.write_image(os.path.join(self.output_dir, "image_group_1_diff.png"), img_group_1_diff)
        self.summarise(img_group_1_diff, os.path.join(self.output_dir, "image_group_1_diff_hist.png"))

        img_group_2_diff = self.cavi_process.subtract_images(files[2], files[3])
        self.cavi_process.write_image(os.path.join(self.output_dir, "image_group_2_diff.png"), img_group_2_diff)
        self.summarise(img_group_2_diff, os.path.join(self.output_dir, "image_group_2_diff_hist.png"))

        groups_min = np.minimum(img_group_1_diff, img_group_2_diff)
        self.cavi_process.write_image(os.path.join(self.output_dir, "groups_min.png"), groups_min)
        self.summarise(groups_min, os.path.join(self.output_dir, "groups_min_hist.png"))

    def summarise(self, img, hist_path):
        valid_pixels = img[img > 0]
        if valid_pixels.size > 0:
            avg_pixel = np.average(valid_pixels)
            max_pixel = np.max(valid_pixels)
            min_pixel = np.min(valid_pixels)
            total_area = valid_pixels.size

            self.cavi_process.log(f"Noise max: {max_pixel}")
            self.cavi_process.log(f"Noise min: {min_pixel}")
            self.cavi_process.log(f"Noise average: {avg_pixel}")
            self.cavi_process.log(f"Noise area: {total_area}")

            plt.hist(valid_pixels.ravel(), bins=50, range=(min_pixel, max_pixel))
            plt.savefig(hist_path)

    def capture_image(self, file_path):
        self.cavi_capture.camera.capture(file_path, 'png')
        return file_path


if __name__ == "__main__":
    main()
