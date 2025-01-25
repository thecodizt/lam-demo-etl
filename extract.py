import pandas as pd
import json
from datetime import datetime
import os
import zipfile
import os

FILES_BLACKLIST = ["schema"]


def save_xlsx_to_csv(source_path, target_path="data/"):
    data = read_xlsx(source_path)

    if not os.path.exists(target_path):
        os.makedirs(target_path)

    for key, value in data.items():
        df = pd.DataFrame(value)
        df.to_csv(f"{target_path}{key}.csv", index=False)

    # zip the files
    os.system(f"zip -r {target_path}/data.zip {target_path}")


def read_xlsx(file_path):
    print("File path: ", file_path)

    # Validate file path
    if not isinstance(file_path, str):
        raise ValueError(f"Expected string file path, got {type(file_path)}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Excel file not found at path: {file_path}")

    excel_file = pd.ExcelFile(file_path)
    data = {}

    for sheet_name in excel_file.sheet_names:
        if sheet_name.lower() in FILES_BLACKLIST:
            continue

        try:
            df = pd.read_excel(
                excel_file,
                sheet_name=sheet_name,
                parse_dates=True,  # Automatically parse date columns
            )

            # Convert DataFrame to a list of dictionaries (records)
            records = df.to_dict(orient="records")

            # Convert datetime objects to epoch time
            for record in records:
                for key, value in record.items():
                    if isinstance(value, (pd.Timestamp, datetime)):
                        record[key] = int(value.timestamp())

            # Store the processed records
            data[sheet_name.lower()] = records

        except Exception as e:
            print(f"Error processing sheet {sheet_name}: {str(e)}")
            continue

    return data


def read_zip(file_path):
    # Get the directory name from zip file path (without .zip extension)
    dir_path = os.path.splitext(file_path)[0]

    # Remove the directory if it already exists
    if os.path.exists(dir_path):
        import shutil

        shutil.rmtree(dir_path)

    # Create a fresh directory
    os.makedirs(dir_path)

    # Extract the zip file contents
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(dir_path)

    # Process all CSV files in the extracted directory
    data = {}
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.endswith(".csv"):
                csv_path = os.path.join(root, file)
                try:
                    # Read CSV file
                    df = pd.read_csv(csv_path)
                    # Convert to records format (list of dictionaries)
                    records = df.to_dict(orient="records")

                    # Use snake_case filename (without extension) as the key
                    key = convert_to_snake_case(os.path.splitext(file)[0])
                    data[key] = records
                except Exception as e:
                    print(f"Error processing {file}: {str(e)}")
                    continue

    return data


# Custom function to convert datetime to epoch time
def datetime_to_epoch(obj):
    if isinstance(obj, (pd.Timestamp, datetime)):
        return int(obj.timestamp())  # Convert to epoch time (seconds since 1970)
    raise TypeError(f"Type {type(obj)} not serializable")


def convert_to_snake_case(string):
    string = string.lower()
    string = string.replace(" ", "_")
    string = string.replace(".", "_")
    return string


def main():
    file_path = "data/sample/sample.xlsx"
    data = convert_xlsx(file_path)
    save_xlsx_to_csv(source_path=file_path, target_path="data/sample/csv/")

    # data = convert_csv(file_path)


if __name__ == "__main__":
    main()
