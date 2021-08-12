import os
import traceback

import pandas as pd
import whetstone
from dotenv import load_dotenv

# from datarobot.utilities import email

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
    grades = ws.get("generic-tags/grades").get("data")
    courses = ws.get("generic-tags/courses").get("data")
    current_users = ws.get("users").get("data")
    archive_users = ws.get("users", params={"archived": True}).get("data")
    roles = ws.get("roles", params={"district": WHETSTONE_DISTRICT_ID}).get("data")
    users = current_users + archive_users

    # load ws users into df
    existing_users = pd.DataFrame(users).convert_dtypes()

    # load import users into df
    import_users = pd.read_json(WHETSTONE_IMPORT_FILE).convert_dtypes()
    import_users.user_internal_id = import_users.user_internal_id.astype("string")
    import_users.coach_internal_id = import_users.coach_internal_id.astype("string")
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
        grade_id = get_matching_record(grades, "name", u["grade_name"]).get("_id")
        course_id = get_matching_record(courses, "name", u["course_name"]).get("_id")
        role_id = get_matching_record(roles, "name", u["role_name"]).get("_id")
        user_id = get_matching_record(users, "internalId", u["user_internal_id"]).get(
            "_id"
        )
        coach_id = get_matching_record(users, "internalId", u["coach_internal_id"]).get(
            "_id"
        )
        school_match = get_matching_record(schools, "name", u["school_name"])
        school_observation_groups = school_match.get("observationGroups", [])
        school_id = school_match.get("_id")

        ## build user payload
        user_payload = {
            "district": WHETSTONE_DISTRICT_ID,
            "name": u["user_name"],
            "email": u["user_email"],
            "internalId": u["user_internal_id"],
            "inactive": u["inactive"],
            "defaultInformation": {
                "school": school_id,
                "gradeLevel": grade_id,
                "course": course_id,
            },
            "coach": coach_id,
            "roles": [role_id],
        }

        ## create or update
        try:
            if not user_id:
                create_resp = ws.post("users", body=user_payload)
                user_id = create_resp.get("_id")
                print(f"\tCreated")
            else:
                ws.put("users", user_id, body=user_payload)
                print(f"\tUpdated")
        except Exception as e:
            print(e)
            # subject = f"Whetstone User Sync Error"
            # email.send_email(subject=subject, body=traceback.format_exc())
            continue

        ## deactivate or reactivate
        if not u["inactive"] and u["archivedAt"] is not pd.NA:
            reactivate_url = f"{ws.base_url}/users/{user_id}/archive"
            ws.frontend_session.put(reactivate_url, params={"value": False})
            print("\tReactivated")
        elif u["inactive"] and u["archivedAt"] is pd.NA:
            ws.delete("users", user_id)
            print(f"\tArchived")

        ## add to observation group
        if school_id:
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
                    "roleId": role_id,
                    "schoolId": school_id,
                    "groupId": group_id,
                }
                ws.post("school-roles", params=update_query, session_type="frontend")
                print(f"\tAdded to {u['group_name']} as {u['role_name']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
        # subject = f"Whetstone User Sync Error"
        # email.send_email(subject=subject, body=traceback.format_exc())
