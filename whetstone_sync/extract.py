import gzip
import json
import os
import pathlib
import traceback

import whetstone
from google.cloud import storage

from settings import ENDPOINTS, USER_ENDPOINTS
from datarobot.utilities import email

WHETSTONE_CLIENT_ID = os.getenv("WHETSTONE_CLIENT_ID")
WHETSTONE_CLIENT_SECRET = os.getenv("WHETSTONE_CLIENT_SECRET")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

WHETSTONE_CLIENT_CREDENTIALS = (WHETSTONE_CLIENT_ID, WHETSTONE_CLIENT_SECRET)
FILE_DIR = pathlib.Path(__file__).absolute().parent


def save_file(file_path, data, gcs_bucket):
    with gzip.open(file_path, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"\tSaved to {file_path}!")

    destination_blob_name = "whetstone/" + "/".join(file_path.parts[-2:])
    blob = gcs_bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)
    print(f"\tUploaded to {destination_blob_name}!")


def main():
    ws = whetstone.Whetstone()
    ws.authorize_client(client_credentials=WHETSTONE_CLIENT_CREDENTIALS)

    gcs_storage_client = storage.Client()
    gcs_bucket = gcs_storage_client.bucket(GCS_BUCKET_NAME)

    generic_tags = ws.get("generic-tags").get("data")
    generic_tags_endpoints = [{"path": f"generic-tags/{t}"} for t in generic_tags]
    all_endpoints = generic_tags_endpoints + ENDPOINTS

    # users
    """
    Whetstone's users endpoint is busted. It'll omit some records and dupe others.
    This is a workaround until they fix it.
    """
    all_users = []
    for e in USER_ENDPOINTS:
        e_path = e.get("path")
        e_params = e.get("params", {})
        print(e)

        try:
            r = ws.get(e_path, params=e_params)
        except Exception as xc:
            print(xc)
            print(traceback.format_exc())
            email_subject = f"Whetstone Extract Error - Users"
            email_body = f"{xc}\n\n{traceback.format_exc()}"
            email.send_email(subject=email_subject, body=email_body)

        count = r.get("count")
        print(f"\tFound {count} records...")

        if count > 0:
            data = r.get("data")
            all_users.extend(data)

    file_dir = FILE_DIR / "data" / "users"
    if not file_dir.exists():
        file_dir.mkdir(parents=True)
        print(f"\tCreated {file_dir}...")

    print(f"Saving {len(all_users)} users...")
    for user in all_users:
        user_id = user.get("_id")
        print(user_id)

        file_path = file_dir / f"{user_id}.json.gz"
        save_file(file_path=file_path, data=user, gcs_bucket=gcs_bucket)

    # all other endpoints
    for e in all_endpoints:
        e_path = e.get("path")
        e_params = e.get("params", {})
        print(e_path)

        e_name = e_path.replace("generic-tags", "").replace("/", "")
        file_dir = FILE_DIR / "data" / e_name
        if not file_dir.exists():
            file_dir.mkdir(parents=True)
            print(f"\tCreated {file_dir}...")

        try:
            r = ws.get(e_path, params=e_params)
        except Exception as xc:
            print(xc)
            print(traceback.format_exc())
            email_subject = f"Whetstone Extract Error - {e_name}"
            email_body = f"{xc}\n\n{traceback.format_exc()}"
            email.send_email(subject=email_subject, body=email_body)
            continue

        count = r.get("count")
        print(f"\tFound {count} records...")
        if count > 0:
            data = r.get("data")

            if "archived" in e_params.keys():
                file_name = f"{e_name}_archived"
            if "lastModified" in e_params.keys():
                file_name = f"{e_name}_{e_params['lastModified']}"

            file_path = file_dir / f"{file_name}.json.gz"
            save_file(file_path=file_path, data=data, gcs_bucket=gcs_bucket)


if __name__ == "__main__":
    try:
        main()
    except Exception as xc:
        print(xc)
        print(traceback.format_exc())
        email_subject = "Whetstone Extract Error"
        email_body = f"{xc}\n\n{traceback.format_exc()}"
        email.send_email(subject=email_subject, body=email_body)
