import gzip
import json
import os
import pathlib
import traceback

import whetstone
from dotenv import load_dotenv
from google.cloud import storage

from datarobot.utilities import email
from settings import ENDPOINTS

load_dotenv()

WHETSTONE_CLIENT_ID = os.getenv("WHETSTONE_CLIENT_ID")
WHETSTONE_CLIENT_SECRET = os.getenv("WHETSTONE_CLIENT_SECRET")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

WHETSTONE_CLIENT_CREDENTIALS = (WHETSTONE_CLIENT_ID, WHETSTONE_CLIENT_SECRET)
PROJECT_PATH = pathlib.Path(__file__).absolute().parent


def main():
    ws = whetstone.Whetstone()
    ws.authorize_client(client_credentials=WHETSTONE_CLIENT_CREDENTIALS)

    generic_tags = ws.get("generic-tags").get("data")
    generic_tags_endpoints = [{"path": f"generic-tags/{t}"} for t in generic_tags]
    all_endpoints = generic_tags_endpoints + ENDPOINTS

    gcs_storage_client = storage.Client()
    gcs_bucket = gcs_storage_client.bucket(GCS_BUCKET_NAME)

    for e in all_endpoints:
        e_path = e.get("path")
        e_params = e.get("params", {})
        print(e_path)

        e_name = e_path.replace("generic-tags", "").replace("/", "")
        file_dir = PROJECT_PATH / "data" / e_name
        if not file_dir.exists():
            file_dir.mkdir(parents=True)
            print(f"\tCreated {file_dir}...")

        try:
            r = ws.get(e_path, params=e_params)

            count = r.get("count")
            print(f"\tFound {count} records...")
            if count > 0:
                data = r.get("data")

                file_name = e_name
                if "archived" in e_params.keys():
                    file_name = f"{file_name}_archived"
                if "lastModified" in e_params.keys():
                    file_name = f"{file_name}_{e_params['lastModified']}"
                file_path = file_dir / f"{file_name}.json.gz"

                with gzip.open(file_path, "wt", encoding="utf-8") as f:
                    json.dump(data, f)
                print(f"\tSaved to {file_path}!")

                destination_blob_name = "whetstone/" + "/".join(file_path.parts[-2:])
                blob = gcs_bucket.blob(destination_blob_name)
                blob.upload_from_filename(file_path)
                print(f"\tUploaded to {destination_blob_name}!")
        except Exception as xc:
            print(xc)
            print(traceback.format_exc())
            email_subject = f"Whetstone Extract Error - {e_name}"
            email_body = f"{xc}\n\n{traceback.format_exc()}"
            email.send_email(subject=email_subject, body=email_body)
            continue


if __name__ == "__main__":
    try:
        main()
    except Exception as xc:
        print(xc)
        print(traceback.format_exc())
        email_subject = "Whetstone Extract Error"
        email_body = f"{xc}\n\n{traceback.format_exc()}"
        email.send_email(subject=email_subject, body=email_body)