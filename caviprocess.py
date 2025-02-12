import configparser
import time
import datetime
import sys
import getopt
import os
import cv2
import numpy as np
import json
import csv
import sqlite3

def main():
    force_reprocess = False
    roi_areas_only = False
    config_path = ""
    print(f"Received config path: {config_path}")

    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:r", ["config=", "reprocess", "roiareas"])
    except getopt.GetoptError:
        print("Usage: caviprocess.py --config <path/to/config.ini> --reprocess --roiareas")
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == "--config":
            config_path = arg
        elif opt == "--reprocess":
            force_reprocess = True
        elif opt == "--roiareas":
            roi_areas_only = True
    
    if not config_path:
        print("Error: Config file path is required.")
        sys.exit(2)
    
    processor = CaviProcess(config_path, force_reprocess, roi_areas_only)
    processor.init_processing()

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
        config = configparser.ConfigParser()
        config.read(self.config_file)
        print(f"Reading from config file: {self.config_file}")
        
        self.output_dir = config.get('capture', 'output_dir')
        self.capture_sequence_name = config.get('capture', 'sequence_name')
        self.capture_light_source = config.get('capture', 'light_source')
        self.intermediates_enabled = config.getboolean('process', 'intermediates_enabled')
        self.outlier_removal_enabled = config.getboolean('process', 'outlier_removal_enabled')
        self.filtering_enabled = config.getboolean('process', 'filtering_enabled')
        self.thresholding_enabled = config.getboolean('process', 'thresholding_enabled')
        self.difference_enabled = config.getboolean('process', 'difference_enabled')
        self.filter_threshold = config.getint('process', 'filter_threshold')
        self.verbose = config.getboolean('process', 'verbose')
        self.roi_enabled = config.getboolean('process', 'roi_enabled')
        self.roi = tuple(map(float, config.get('process', 'roi').split(',')))

    def create_directories(self):
        os.makedirs(self.output_dir, exist_ok=True)
        self.sequence_path = os.path.join(self.output_dir, self.capture_sequence_name)
        self.process_dir = os.path.join(self.sequence_path, "processed")
        self.captures_csv_path = os.path.join(self.sequence_path, "captures.csv")
        os.makedirs(self.process_dir, exist_ok=True)

    def create_files(self):
        self.log_file = os.path.join(self.process_dir, "log.txt")

    def open_db(self):
        db_path = os.path.join(self.sequence_path, 'capture.db')
        if not os.path.exists(db_path):
            self.log_error(f"Exiting: can't find captures db: {db_path}")
            sys.exit()
        self.db_conn = sqlite3.connect(db_path)

    def init_processing(self):
        if self.roi_areas_only:
            self.init_area_processing()
            return

        if self.force_reprocess:
            self.db_conn.execute("UPDATE captures SET processed = 0, processing = 0")
            self.db_conn.commit()

        while True:
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT id, filename, timestamp, skip, processed FROM captures ORDER BY id ASC")
                rows = cursor.fetchall()
                previous_row = None
                
                for row in rows:
                    if previous_row and not row[4]:
                        self.db_conn.execute("UPDATE captures SET processing = 1 WHERE id = ?", (row[0],))
                        self.db_conn.commit()
                        area = self.process(os.path.join(self.sequence_path, row[1]), os.path.join(self.sequence_path, previous_row[1]))
                        self.db_conn.execute("UPDATE captures SET processed = 1, processing = 0, area = ? WHERE id = ?", (area, row[0]))
                        self.db_conn.commit()
                    previous_row = row
                
                if self.force_reprocess:
                    self.log_info("Reprocessing complete")
                    sys.exit()
            except sqlite3.OperationalError:
                self.log_info("Database locked - trying again in 1 second")
                time.sleep(1)
            except KeyboardInterrupt:
                sys.exit()
            time.sleep(6)

    def process(self, file_1, file_2):
        img_1 = cv2.imread(file_1, 0)
        img_2 = cv2.imread(file_2, 0) if self.difference_enabled else None
        
        if self.difference_enabled and img_2 is not None:
            output = cv2.absdiff(img_1, img_2)
        else:
            output = img_1
        
        if self.filtering_enabled:
            output[output < self.filter_threshold] = 0
        
        if self.thresholding_enabled:
            _, output = cv2.threshold(output, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        cv2.imwrite(os.path.join(self.process_dir, os.path.basename(file_1)), output)
        area = np.count_nonzero(output)
        return area

    def log_info(self, entry):
        print(f"INFO: {entry}")
        with open(self.log_file, 'a') as log:
            log.write(f"{entry}\n")

    def log_error(self, entry):
        print(f"ERROR: {entry}")
        with open(self.log_file, 'a') as log:
            log.write(f"{entry}\n")

if __name__ == '__main__':
    main()
