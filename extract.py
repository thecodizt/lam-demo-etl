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
    """
    Read data from a zip file containing CSV files

    Args:
        file_path: Path to the zip file

    Returns:
        Dictionary containing the data from each CSV file
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ZIP file not found at path: {file_path}")

    data = {}

    with zipfile.ZipFile(file_path, "r") as zip_ref:
        # List all CSV files in the zip
        csv_files = [f for f in zip_ref.namelist() if f.endswith(".csv")]

        for csv_file in csv_files:
            # Get the type name from the file name (remove .csv extension and path)
            type_name = os.path.splitext(os.path.basename(csv_file))[0]

            if type_name.lower() in FILES_BLACKLIST:
                continue

            # Read CSV file directly from zip, try different encodings
            encodings = ['utf-8', 'latin1', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    with zip_ref.open(csv_file) as f:
                        df = pd.read_csv(f, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise UnicodeDecodeError(f"Failed to decode {csv_file} with any of the attempted encodings: {encodings}")
                
            data[type_name] = df.to_dict(orient="records")

    return data


def save_timestamped_data(data, timestamp=None):
    """
    Save data to a timestamped zip file

    Args:
        data: Dictionary containing the data to save
        timestamp: Optional timestamp to use, defaults to current time
    """
    if timestamp is None:
        timestamp = int(datetime.now().timestamp())

    # Create timestamped directory if it doesn't exist
    if not os.path.exists("data/timestamped"):
        os.makedirs("data/timestamped")

    # Create temporary directory for CSV files
    temp_dir = f"data/temp_{timestamp}"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    try:
        # Save each data type to a CSV file
        for type_name, records in data.items():
            if type_name.lower() in FILES_BLACKLIST:
                continue

            df = pd.DataFrame(records)
            df.to_csv(f"{temp_dir}/{type_name}.csv", index=False)

        # Create zip file
        zip_path = f"data/timestamped/{timestamp}.zip"
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

    finally:
        # Clean up temporary directory
        import shutil

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def get_available_timestamps():
    """
    Get list of available timestamps from the timestamped directory

    Returns:
        List of timestamps (as integers)
    """
    if not os.path.exists("data/timestamped"):
        return []

    timestamps = []
    for file in os.listdir("data/timestamped"):
        if file.endswith(".zip"):
            try:
                timestamp = int(file.split(".")[0])
                timestamps.append(timestamp)
            except ValueError:
                continue

    return sorted(timestamps)


def main():
    file_path = "data/sample/sample.xlsx"
    data = read_xlsx(file_path)
    save_xlsx_to_csv(source_path=file_path, target_path="data/sample/csv/")
    save_timestamped_data(data)


if __name__ == "__main__":
    main()
