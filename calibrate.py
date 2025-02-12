from cavicapture import CaviCapture
from process import CaviProcess
import sys, os, getopt
import time, datetime
import numpy as np
import matplotlib.pyplot as plt

def main():

  config_path = './config.ini' # default

  try:
    opts, args = getopt.getopt(sys.argv[1:], "c", ["config="])
  except getopt.GetoptError:
    print("Argument error")
    sys.exit(2)
  for opt, arg in opts:
    if opt in ("--config"):
      config_path = arg

  calibrator = CaviCalibrate(config_path)
  calibrator.init_calibration()

class CaviCalibrate:

  def __init__(self, config_path):

    self.output_dir = "./calibration"

    if not os.path.exists(self.output_dir):
      os.makedirs(self.output_dir)    

    self.output_dir = self.output_dir + "/" + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')

    if not os.path.exists(self.output_dir):
      os.makedirs(self.output_dir)    

    self.cavi_capture = CaviCapture(config_path)
    self.cavi_capture.log_file = self.output_dir + "/capture.log.txt"
    self.cavi_capture.get_ini_config()
    self.cavi_capture.setup_gpio()
    self.cavi_capture.setup_camera()

    self.cavi_process = CaviProcess(self.output_dir)
    self.cavi_process.log_file = self.output_dir + "/process.log.txt"

  def init_calibration(self):

    files = []

    self.cavi_capture.lights(True)
    time.sleep(3) # Let lights settle
    files.append(self.capture_image(self.output_dir + "/" + "image_1.png"))
    files.append(self.capture_image(self.output_dir + "/" + "image_2.png"))
    files.append(self.capture_image(self.output_dir + "/" + "image_3.png"))
    files.append(self.capture_image(self.output_dir + "/" + "image_4.png"))
    self.cavi_capture.lights(False)

    self.process_files(files)

  def process_files(self, files):

    file_1 = files[0]
    file_2 = files[1]
    file_3 = files[2]
    file_4 = files[3]
    
    # Get the image difference and summary using 2 images
    # diff = self.cavi_process.subtract_images(file_1, file_2)
    # self.cavi_process.write_image(self.output_dir + "/diff.png", diff)
    # self.summarise(diff, self.output_dir + "/noise_hist.png")

    # Image difference first two and last two
    img_group_1_diff = self.cavi_process.subtract_images(file_1, file_2)
    self.cavi_process.write_image(self.output_dir + "/image_group_1_diff.png", img_group_1_diff)
    self.summarise(img_group_1_diff, self.output_dir + "/image_group_1_diff_hist.png")

    img_group_2_diff = self.cavi_process.subtract_images(file_3, file_4)
    self.cavi_process.write_image(self.output_dir + "/image_group_2_diff.png", img_group_2_diff)
    self.summarise(img_group_2_diff, self.output_dir + "/image_group_2_diff_hist.png")

    groups_min = np.minimum(img_group_1_diff, img_group_2_diff)
    self.cavi_process.write_image(self.output_dir + "/groups_min.png", groups_min)
    self.summarise(groups_min, self.output_dir + "/groups_min_hist.png")

    # diff = self.cavi_process.subtract_images(self.output_dir + "/image_1_average.png", self.output_dir + "/image_2_average.png")
    # self.cavi_process.write_image(self.output_dir + "/image_average_diff.png", diff)
    # self.summarise(diff, self.output_dir + "/image_average_noise_hist.png")

  def summarise(self, img, hist_path):

    average_pixel = np.average(img[img>0])
    max_pixel = np.max(img[img>0])
    min_pixel = np.min(img[img>0])
    total_area = len(img[img>0])

    self.cavi_process.log("Noise max: " + str(max_pixel))
    self.cavi_process.log("Noise min: " + str(min_pixel))
    self.cavi_process.log("Noise average: " + str(average_pixel))
    self.cavi_process.log("Noise area: " + str(total_area))

    plt.hist(img.ravel(),max_pixel,[min_pixel,max_pixel])
    plt.savefig(hist_path)

  def gen_file_path(self):
    return self.output_dir + "/" + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + ".png"

  def capture_image(self, file_path):
    self.cavi_capture.camera.capture(file_path, 'png')
    return file_path

if __name__ == '__main__':
    main()
