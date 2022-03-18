import argparse
import json
import os
import pathlib
import re
import traceback

import pandas as pd
import sqlalchemy as sa

DB_TYPE = os.getenv("DB_TYPE")
DB_API = os.getenv("DB_API")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

PROJECT_PATH = pathlib.Path(__file__).absolute().parent


def main(config):
    if config:
        config_name = re.split("[^a-zA-Z]", config)[-2]
        with open(config) as f:
            queries = json.load(f)
    else:
        raise Exception("Missing argument: --config /path/to/config.json")

    db_engine = sa.create_engine(
        f"{DB_TYPE}+{DB_API}://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    print("Extracting from database...")

    # run all queries contained in config file
    for i, q in enumerate(queries):
        sql = q["query"]
        print(f"\t{i + 1}) {sql}")

        try:
            df = pd.read_sql_query(con=db_engine, sql=sql)
            print("\t\tSuccess!")
        except Exception as xc:
            print("\t\tFailure!")
            print(xc)
            print(traceback.format_exc())
            continue

        data_path = PROJECT_PATH / "data"
        file_name = q["output"]["file"].get("name")
        file_extension = q["output"]["file"]["extension"]
        file_path = data_path / config_name / f"{file_name}.{file_extension}"

        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True)

        # save to configured file format
        print(f"\t\tExporting to {file_path}...")
        options = q["output"]["file"].get("options", {})
        # CSV/TSV
        if file_extension in ["csv", "txt", "csv.ready"]:
            df.to_csv(file_path, **options)
        # JSON
        elif file_extension == "json":
            df.to_json(file_path, **options)
        print("\t\t\tSuccess!")


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-C", "--config", help="Config file", required=False)
        args = parser.parse_args()
        main(args.config)
    except Exception as xc:
        print(xc)
        print(traceback.format_exc())
