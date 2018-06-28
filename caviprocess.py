#!/usr/bin/python

from ConfigParser import SafeConfigParser
import time, datetime
import sys
import getopt
import os
import cv2
import numpy as np
import ntpath
import json
import csv
import sqlite3

def main():

  force_reprocess = False
  roi_areas_only = False

  try:
      opts, args = getopt.getopt(sys.argv[1:], "c:r", ["config=", "reprocess", "roiareas"])
  except getopt.GetoptError:
      print("caviprocess.py --config <path/to/config.ini> --reprocess --roiareas")
      sys.exit(2)
  for opt, arg in opts:
      if opt in ("--config"):
        config_path = arg
      elif opt in ("--reprocess"):
        force_reprocess = True
      elif opt in ("--roiareas"):
        roi_areas_only = True

  processor = CaviProcess(config_path, force_reprocess, roi_areas_only)
  processor.init_processing()

  return

class CaviProcess:
  
  def __init__(self, config_file, force_reprocess, roi_areas_only):

    self.force_reprocess = force_reprocess
    self.roi_areas_only = roi_areas_only
    self.config_file = config_file
    self.load_config()    
    self.create_directories()
    self.create_files()
    self.open_db()

  def load_config(self):

    config = SafeConfigParser()
    config.read(self.config_file)

    print "Reading from config file: " + self.config_file

    # Capture config
    self.output_dir                 = config.get('capture', 'output_dir')
    self.capture_sequence_name      = config.get('capture', 'sequence_name')
    self.capture_light_source       = config.get('capture', 'light_source')
    
    # Processing config
    self.intermediates_enabled      = config.getboolean('process', 'intermediates_enabled')
    self.outlier_removal_enabled    = config.getboolean('process', 'outlier_removal_enabled')
    self.filtering_enabled          = config.getboolean('process', 'filtering_enabled')
    self.thresholding_enabled       = config.getboolean('process', 'thresholding_enabled')
    self.difference_enabled         = config.getboolean('process', 'difference_enabled')
    self.filter_threshold           = config.getint('process', 'filter_threshold')
    self.verbose                    = config.getboolean('process', 'verbose')
    self.roi_enabled                = config.getboolean('process', 'roi_enabled')

    roi_concat_string = config.get('process', 'roi')
    self.roi = tuple([float(n) for n in roi_concat_string.split(",")])


  def create_directories(self):

    if not self.output_dir.endswith("/"):
      self.output_dir = self.output_dir + "/"

    self.sequence_path = self.output_dir + self.capture_sequence_name + "/"
    self.process_dir = self.sequence_path + "processed/"
    self.captures_csv_path = self.sequence_path + "captures.csv"

    if not os.path.exists(self.process_dir):
      os.makedirs(self.process_dir)

  def create_files(self):
    self.log_file = self.process_dir + "log.txt"

  def open_db(self):
    if not os.path.exists(self.sequence_path + 'capture.db'):
      self.log_error("Exiting: can't find captures db: " + self.sequence_path + "capture.db")
      sys.exit()

    self.db_conn = sqlite3.connect(self.sequence_path + 'capture.db')

  def init_processing(self):
    id, filename, timestamp, skip, processed = 0, 1, 2, 3, 4

    if self.roi_areas_only:
      self.init_area_processing()
      return

    if self.force_reprocess:
      self.db_conn.execute("UPDATE captures SET processed = 0, processing = 0")
      self.db_conn.commit()

    while True:
      try:
        conn_cursor = self.db_conn.cursor()
        conn_cursor.execute("SELECT id, filename, timestamp, skip, processed FROM captures ORDER BY id ASC")
        rows = conn_cursor.fetchall()
        previous_row = None 
        for row in rows:
          if previous_row and not row[processed]:
            self.db_conn.execute("UPDATE captures SET processing = 1 WHERE id = " + str(row[id]))
            self.db_conn.commit()
            area = self.process(self.sequence_path + row[filename], self.sequence_path + previous_row[filename])
            # print "Updating record"
            self.db_conn.execute("UPDATE captures SET processed = 1, processing = 0, area = ? WHERE id = ?", (area, row[id]))
            self.db_conn.commit()
          previous_row = row
        if self.force_reprocess:
           # Only do reprocessing once
          self.log_info("Reprocessing complete")
          sys.exit()  
      except sqlite3.OperationalError:
        self.log_info("database locked - trying again in 1 second")
        time.sleep(1)
      except KeyboardInterrupt:
        sys.exit()
        self.db_conn.close()
      time.sleep(6)

  def init_area_processing(self):
    id, filename, timestamp, skip, processed = 0, 1, 2, 3, 4

    while True:
      try:
        conn_cursor = self.db_conn.cursor()
        conn_cursor.execute("SELECT id, filename, timestamp, skip, processed FROM captures ORDER BY id ASC")
        rows = conn_cursor.fetchall()
        previous_row = None 
        for row in rows:
          if previous_row and row[processed]:
            area = self.process_area(self.sequence_path + row[filename])
            self.db_conn.execute("UPDATE captures SET area = ? WHERE id = ?", (area, row[id]))
            self.db_conn.commit()
          previous_row = row
        self.log_info("ROI areas processed")
        sys.exit()  
      except sqlite3.OperationalError:
        self.log_info("database locked - trying again in 1 second")
        time.sleep(1)
      except KeyboardInterrupt:
        # print "Processing Interrupted"
        sys.exit()
      time.sleep(6)

  def process_area(self, file_1):
    self.log_info("Processing ROI area only")
    self.timer_start_time = datetime.datetime.now()
    self.start_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    self.log_info("Start time: " + self.start_time)
    file_name = self.extract_filename(file_1)
    self.output_filename = file_name;

    processed_image_path = self.process_dir + self.output_filename + ".png"
    if not os.path.exists(processed_image_path):
      self.log_error("Processed file required for roi areas calculation: couldn't find " + self.process_dir + self.output_filename + ".png")
      return 0
    processed_image = cv2.imread(self.process_dir + self.output_filename + ".png", 0)
    return self.get_roi_area_total(processed_image)
    
  
  def process(self, file_1, file_2):

    self.timer_start_time = datetime.datetime.now()
    self.start_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    self.log_info("Start time: " + self.start_time)
    
    file_1_filename = self.extract_filename(file_1)
    self.output_filename = file_1_filename;

    if self.intermediates_enabled:
      intermediates_path = self.process_dir + self.output_filename + "/"
      if not os.path.exists(intermediates_path):
        os.makedirs(intermediates_path)

    if self.roi_areas_only:
      self.log_info("Processing ROI area only")
      processed_image_path = self.process_dir + self.output_filename + ".png"
      if not os.path.exists(processed_image_path):
        self.log_error("Processed file required for roi areas calculation: couldn't find " + self.process_dir + self.output_filename + ".png")
        return 0
      processed_image = cv2.imread(self.process_dir + self.output_filename + ".png", 0)
      return self.get_roi_area_total(processed_image)

    img_1 = cv2.imread(file_1, 0)

    if self.difference_enabled:
      img_2 = cv2.imread(file_2, 0)
      self.log_info("File 1: " + file_1)
      self.log_info("File 2: " + file_2)
    else:
      output = img_1
      self.log_info("File: " + file_1)
      self.log_info("Difference skipped")

    # Process Image Difference
    if self.difference_enabled:
      self.start_timer()
      if self.capture_light_source == "Above":
        output = self.subtract_images(img_1, img_2)
      else:
        output = self.subtract_images(img_2, img_1)
      if self.intermediates_enabled:
        self.write_image(intermediates_path + self.output_filename + "_difference.png", output)
      self.log_info("Difference completed: " + str(self.stop_timer_return_seconds()) + "s (" + self.capture_light_source + " sample light source)")

    # Filter out pixels below threshold
    if self.filtering_enabled:
      self.start_timer()
      output = self.filter_pixels(output)
      if self.intermediates_enabled:
        self.write_image(intermediates_path + self.output_filename + "_pixels_filtered.png", output)
      self.log_info("Filtering completed: " + str(self.stop_timer_return_seconds()) + "s")
    else:
      self.log_info("Filtering skipped")

    # Remove outliers
    if self.outlier_removal_enabled:
      self.start_timer()
      output, blurred_image = self.median_filter_using_median_blur("bright", 3, output)
      if self.intermediates_enabled:
        self.write_image(intermediates_path + self.output_filename + "_median_blurred.png", blurred_image)
        self.write_image(intermediates_path + self.output_filename + "_outliers_removed.png", output)
      self.log_info("Outlier removal completed: " + str(self.stop_timer_return_seconds()) + "s")
    else:
      self.log_info("Outlier removal skipped")

    # Apply threshold
    if self.thresholding_enabled:
      self.start_timer()
      output = self.apply_threshold(output);
      if self.intermediates_enabled:
        self.write_image(intermediates_path + self.output_filename + "_thresholded.png", output)
      self.log_info("Thresholding completed: " + str(self.stop_timer_return_seconds()) + "s")
    else:
      self.log_info("Thresholding skipped")
    
    # Final output
    self.write_image(self.process_dir + self.output_filename + ".png", output)

    # Calculate the area
    if self.roi_enabled == True:
      area = self.get_roi_area_total(output)
      self.log_info("Embolism total ROI area: " + str(area))
    else:
      area = len(output[output>0])
      self.log_info("Embolism total area: " + str(area))
    
    return area

  def get_roi_area_total(self, image):

    img_width = int(image.shape[1])
    img_height = int(image.shape[0])

    height_rel_image_height = self.roi[0]
    width_rel_image_width = self.roi[1]
    top_rel_image_height = self.roi[2]
    left_rel_image_width = self.roi[3]

    start_x = int(left_rel_image_width * img_width)
    end_x = int(start_x + (width_rel_image_width * img_width))
    start_y = int(top_rel_image_height * img_height)
    end_y = int(start_y + (height_rel_image_height * img_height))
    roi = image[start_y:end_y, start_x:end_x].copy()
    area = len(roi[roi>0])
    return area

  def extract_filename(self, path):
    head, tail = ntpath.split(path)
    filename = tail or ntpath.basename(head)
    name, ext = filename.split(".")
    return name

  def apply_threshold(self, image):
    ret2,image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)  
    return image

  def write_image(self, path, file):
    cv2.imwrite(path, file)

  def start_timer(self):
    self.timer_start_time = datetime.datetime.now()

  def stop_timer_return_seconds(self):
    return (datetime.datetime.now() - self.timer_start_time).total_seconds()

  def subtract_images(self, img_1, img_2):
    # return cv2.absdiff(img_1, img_2)
    return cv2.subtract(img_1, img_2)

  def average_images(self, file_1, file_2):

    #read images and convert to 8 bit
    img_1 = cv2.imread(file_1, 0)
    img_2 = cv2.imread(file_2, 0)
    
    return cv2.addWeighted(img_1, 0.5, img_2, 0.5, 0)

  def filter_pixels(self, image):

    img_width = int(image.shape[1])
    img_height = int(image.shape[0])

    filter_count = 0

    for y in range(0, img_height):
      for x in range(0, img_width):
        if image[y,x] < self.filter_threshold:
          image[y,x] = 0
          filter_count += 1
    
    return image

  def median_filter_using_median_blur(self, bright_or_dark, radius, image):
    
    counter = 0

    output = image.copy()
    median_blurred_image = cv2.medianBlur(output, radius)

    img_width = int(image.shape[1])
    img_height = int(image.shape[0])

    median_radius_max = radius
    median_radius_min = radius * -1

    #run comparison loop
    for y in range(0, img_height):
      for x in range(0, img_width):
        
        surrounding_pixel_values = []
        
        surrounding_pixel_median = median_blurred_image[y,x]
          
        if(bright_or_dark=="dark" or bright_or_dark=="both"):
          if(surrounding_pixel_median >= image[y,x]):
            output[y,x] = surrounding_pixel_median
            counter += 1
          
        if(bright_or_dark=="bright" or bright_or_dark=="both"):
          if(surrounding_pixel_median <= image[y,x]):
            output[y,x] = surrounding_pixel_median
            counter += 1

    return output, median_blurred_image

  def log(self, entry):
    log = open(self.log_file, 'a')  
    log.write(str(entry) + '\n')
    log.close()

  def log_info(self, entry):
    self.log(str(entry))
    if(self.verbose):
      print 'info|' + str(entry)
      sys.stdout.flush()

  def log_db(self, entry):
    self.log(str(entry))
    if(self.verbose):
      print 'db|' + str(entry)
      sys.stdout.flush()
  
  def log_error(self, entry):
    self.log(str(entry))
    if(self.verbose):
      print 'error|' + str(entry)
      sys.stdout.flush()

  def write_areas(self, entry):
    log = open(self.areas_file, 'a')  
    log.write(str(entry) + '\n')
    log.close()
      
if __name__ == '__main__':
    main()