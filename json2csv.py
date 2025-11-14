"""
  Convert a json list of objects to a CSV file.

  Allows one to load temperature data into 
  libreoffice and graph it. 
"""

import argparse
import json
import csv

def json_to_csv(input_json, output_csv):
    # Load JSON data
    with open(input_json, 'r') as f:
        data = json.load(f)

    # Check if data is a list
    if not isinstance(data, list):
        raise ValueError("JSON data should be a list of objects")

    # Open CSV file for writing
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)

        # Write header (keys of the first object)
        if data:
            writer.writerow(data[0].keys())

        # Write rows
        for row in data:
            writer.writerow(row.values())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert JSON to CSV')
    parser.add_argument('input_json', help='Input JSON filename')
    parser.add_argument('output_csv', help='Output CSV filename')
    args = parser.parse_args()

    json_to_csv(args.input_json, args.output_csv)
    print(f"Successfully converted {args.input_json} to {args.output_csv}")
