import os
import traceback

import pandas as pd
import whetstone
from dotenv import load_dotenv

from datarobot.utilities import email

load_dotenv()

WHETSTONE_CLIENT_ID = os.getenv("WHETSTONE_CLIENT_ID")
WHETSTONE_CLIENT_SECRET = os.getenv("WHETSTONE_CLIENT_SECRET")
WHETSTONE_USERNAME = os.getenv("WHETSTONE_USERNAME")
WHETSTONE_PASSWORD = os.getenv("WHETSTONE_PASSWORD")
WHETSTONE_DISTRICT_ID = os.getenv("WHETSTONE_DISTRICT_ID")
WHETSTONE_IMPORT_FILE = os.getenv("WHETSTONE_IMPORT_FILE")

WHETSTONE_CLIENT_CREDENTIALS = (WHETSTONE_CLIENT_ID, WHETSTONE_CLIENT_SECRET)


def get_matching_record(data, key, match_value):
    return next(
        iter([d for d in data if d.get(key) == match_value and d.get(key) != ""]), {}
    )


def main():
    ws = whetstone.Whetstone()
    ws.authorize_client(client_credentials=WHETSTONE_CLIENT_CREDENTIALS)
    ws.authorize_frontend(
        district_id=WHETSTONE_DISTRICT_ID,
        username=WHETSTONE_USERNAME,
        password=WHETSTONE_PASSWORD,
    )

    # pull current data
    schools = ws.get("schools").get("data")
    current_users = ws.get("users").get("data")
    archive_users = ws.get("users", params={"archived": True}).get("data")
    users = current_users + archive_users

    # load ws users into df
    existing_users = pd.DataFrame(users).convert_dtypes()

    # load import users into df
    import_users = pd.read_json(WHETSTONE_IMPORT_FILE).convert_dtypes()
    import_users.user_internal_id = import_users.user_internal_id.astype("string")
    import_users.inactive = import_users.inactive.astype(bool)
    import_users = import_users.fillna("")

    # merge dfs
    merge_df = import_users.merge(
        right=existing_users[["internalId", "archivedAt", "inactive"]],
        how="left",
        left_on="user_internal_id",
        right_on="internalId",
        suffixes=("", "_ws"),
    )
    merge_df.inactive_ws = merge_df.inactive_ws.fillna(False)
    merge_users = merge_df.to_dict(orient="records")

    for u in merge_users:
        # skip if inactive and already archived
        if u["inactive"] and u["inactive_ws"] and u["archivedAt"] is not pd.NA:
            continue

        print(f"{u['user_name']} ({u['user_internal_id']})")

        # get IDs
        user_id = get_matching_record(users, "internalId", u["user_internal_id"]).get(
            "_id"
        )
        school_match = get_matching_record(schools, "_id", u["school_id"])
        school_observation_groups = school_match.get("observationGroups", [])

        # restore
        if not u["inactive"] and u["archivedAt"] is not pd.NA:
            ws.put(
                "users",
                record_id=f"{user_id}/restore",
                params={"district": WHETSTONE_DISTRICT_ID},
            )
            print("\tReactivated")

        # build user payload
        user_payload = {
            "district": WHETSTONE_DISTRICT_ID,
            "name": u["user_name"],
            "email": u["user_email"],
            "internalId": u["user_internal_id"],
            "inactive": u["inactive"],
            "defaultInformation": {
                "school": u["school_id"],
                "gradeLevel": u["grade_id"],
                "course": u["course_id"],
            },
            "coach": u["coach_id"],
            "roles": [u["role_id"]],
        }

        # create or update
        try:
            if not user_id:
                create_resp = ws.post("users", body=user_payload)
                user_id = create_resp.get("_id")
                print("\tCreated")
            else:
                ws.put("users", user_id, body=user_payload)
        except Exception as xc:
            print(xc)
            print(traceback.format_exc())
            email_subject = "Whetstone User Sync Error"
            email_body = (
                f"{u['user_name']} ({u['user_internal_id']})\n\n"
                f"{xc}\n\n"
                f"{traceback.format_exc()}"
            )
            email.send_email(subject=email_subject, body=email_body)
            continue

        # archive
        if u["inactive"] and u["archivedAt"] is pd.NA:
            ws.delete("users", user_id)
            print("\tArchived")
            continue

        # add to observation group
        if u["school_id"]:
            group_match = get_matching_record(
                school_observation_groups, "name", u["group_name"]
            )
            group_id = group_match.get("_id")
            group_type_match = group_match[u["group_type"]]
            group_membership_match = get_matching_record(
                group_type_match, "_id", user_id
            )

            if not group_membership_match and not u["inactive"]:
                update_query = {
                    "userId": user_id,
                    "roleId": u["role_id"],
                    "schoolId": u["school_id"],
                    "groupId": group_id,
                }
                ws.post("school-roles", params=update_query, session_type="frontend")
                print(f"\tAdded to {u['group_name']} as {u['role_name']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as xc:
        print(xc)
        print(traceback.format_exc())
        email_subject = "Whetstone User Sync Error"
        email.send_email(subject=email_subject, body=traceback.format_exc())
