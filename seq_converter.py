import configparser
import sqlite3
import sys
import os
import getopt
import time
import datetime
import glob
from shutil import copyfile


def main():
    input_directory = ""
    output_directory = ""
    file_mask = ""
    sequence_name = ""
    config_path = ""

    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:i:o:s:f:",
                                   ["config=", "input_dir=", "output_dir=", "sequence_name=", "file_mask="])
    except getopt.GetoptError:
        print("Usage: seq_converter.py --config <path/to/config.ini> --input_dir <path/to/capture/directory> "
              "--output_dir <path/to/new/directory> --sequence_name <name> --file_mask <mask>")
        sys.exit(2)

    for opt, arg in opts:
        if opt == "--config":
            config_path = arg
        elif opt == "--input_dir":
            input_directory = arg
        elif opt == "--output_dir":
            output_directory = arg
        elif opt == "--file_mask":
            file_mask = arg
        elif opt == "--sequence_name":
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
        sql = "DELETE FROM captures;"
        self.db_conn.execute(sql)
        self.db_conn.commit()
        self.find_captures()
        self.write_config()

    def write_config(self):
        self.config.set("capture", "output_dir", self.output_directory.rstrip("/"))
        self.config.set("capture", "sequence_name", self.sequence_name)

        with open(os.path.join(self.output_sequence_path, "config.ini"), "w") as config_file:
            self.config.write(config_file)

    def find_captures(self):
        for file_path in glob.glob(os.path.join(self.input_directory, self.file_mask)):
            print(f"Processing file: {file_path}")
            file_name = os.path.basename(file_path)
            name, _ = os.path.splitext(file_name)
            try:
                file_time = datetime.datetime.strptime(name, "%Y%m%d-%H%M%S")
            except ValueError:
                print(f"Skipping file {file_name}, invalid timestamp format.")
                continue

            sql = "INSERT INTO captures (filename, timestamp, skip, processing, processed) VALUES (?, ?, 0, 0, 0);"
            self.db_conn.execute(sql, (file_name, file_time.strftime("%Y%m%d-%H%M%S")))
            self.db_conn.commit()
            copyfile(file_path, os.path.join(self.output_sequence_path, file_name))

    def setup_directories(self):
        self.input_directory = os.path.abspath(self.input_directory)
        self.output_directory = os.path.abspath(self.output_directory)
        self.output_sequence_path = os.path.join(self.output_directory, self.sequence_name)

        os.makedirs(self.output_directory, exist_ok=True)
        os.makedirs(self.output_sequence_path, exist_ok=True)

    def load_config(self):
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file)

    def setup_db(self):
        self.db_conn = sqlite3.connect(os.path.join(self.output_sequence_path, "capture.db"))
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                skip INTEGER NOT NULL,
                processed INTEGER NOT NULL,
                processing INTEGER NOT NULL,
                area REAL
            );
        """)
        self.db_conn.commit()


if __name__ == "__main__":
    main()
