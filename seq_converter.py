#!/usr/bin/python

from ConfigParser import SafeConfigParser
import sqlite3
import sys, os, getopt
import time, datetime
import glob
import string
from datetime import datetime
from shutil import copyfile

def main():

    input_directory = ''
    output_directory = ''
    file_mask = ''
    sequence_name = ''

    try:
      opts, args = getopt.getopt(sys.argv[1:], "c:i:o:s:f:", ["config=", "input_dir=", "output_dir=", "sequence_name=", "file_mask="])
    except getopt.GetoptError:
      print("seq_converter.py --config <path/to/config.ini> --input_dir <path/to/capture/directory> --output_dir <path/to/new/directory --sequence_name= <name> --file_mask <mask>")
      sys.exit(2)
    
    for opt, arg in opts:
      if opt in ("--config"):
        config_path = arg
      elif opt in ("--input_dir"):
        input_directory = arg
      elif opt in ("--output_dir"):
        output_directory = arg
      elif opt in ("--file_mask"):
        file_mask = arg
      elif opt in ("--sequence_name"):
        sequence_name = arg
      
    cavi_converter = CaviConverter(config_path, input_directory, output_directory, file_mask, sequence_name)
    cavi_converter.init()

class CaviConverter:      

  def __init__(self, config_file, input_directory, output_directory, file_mask, sequence_name):
      
    self.config_file = config_file  
    self.input_directory = input_directory  
    self.output_directory = output_directory  
    self.file_mask = file_mask  
    self.sequence_name = sequence_name  

    self.setup_directories()
    self.setup_db()
    self.load_config()

  def init(self):

    # Clear the new db
    sql = "DELETE FROM captures;"
    self.db_conn.execute(sql)
    self.db_conn.commit()
    self.find_captures()
    self.write_config()

  def write_config(self):

    self.config.set('capture', 'output_dir', self.output_directory.rstrip("/"));
    self.config.set('capture', 'sequence_name', self.sequence_name);

    with open(self.output_sequence_path + "/config.ini", 'w') as config_file:
      self.config.write(config_file)    

  def find_captures(self):

    # print(glob.glob("/home/adam/*.txt"))
    for file_path in glob.glob(self.input_directory + self.file_mask):
      print "File " + file_path + "(" + os.path.basename(file_path) + ")"
      file_name = os.path.basename(file_path)
      name = os.path.basename(file_path).replace(".png", "")
      file_time = datetime.strptime(name, '%Y%m%d-%H%M%S')
      print file_time.strftime('%Y%m%d-%H%M%S')
      sql = "INSERT INTO captures (filename, timestamp, skip, processing, processed) VALUES ('" + file_name + "', '" + file_time.strftime('%Y%m%d-%H%M%S') + "', 0, 0, 0);"
      self.db_conn.execute(sql)
      self.db_conn.commit()
      copyfile(file_path,  self.output_sequence_path + "/" + file_name)


  def setup_directories(self):
    
    if not self.input_directory.endswith("/"):
      self.input_directory = self.input_directory + "/"
    
    if not self.output_directory.endswith("/"):
      self.output_directory = self.output_directory + "/"

    self.output_sequence_path = self.output_directory + self.sequence_name     

    if not os.path.exists(self.output_directory):
      os.makedirs(self.output_directory)

    if not os.path.exists(self.output_sequence_path):
      os.makedirs(self.output_sequence_path)

  def load_config(self):

    self.config = SafeConfigParser()
    self.config.read(self.config_file)

  def setup_db(self):
    self.db_conn = sqlite3.connect(self.output_sequence_path + '/capture.db')
    self.db_conn.execute('''CREATE TABLE IF NOT EXISTS captures
            (id INTEGER PRIMARY KEY,
            filename CHAR(50) NOT NULL,
            timestamp CHAR(50) NOT NULL,
            skip INT NOT NULL,
            processed INT NOT NULL,
            processing INT NOT NULL,
            area REAL);''')

if __name__ == '__main__':
    main()
