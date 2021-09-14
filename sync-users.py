import json
import os
import traceback

import whetstone
from dotenv import load_dotenv

load_dotenv()

WHETSTONE_CLIENT_ID = os.getenv("WHETSTONE_CLIENT_ID")
WHETSTONE_CLIENT_SECRET = os.getenv("WHETSTONE_CLIENT_SECRET")
WHETSTONE_USERNAME = os.getenv("WHETSTONE_USERNAME")
WHETSTONE_PASSWORD = os.getenv("WHETSTONE_PASSWORD")
WHETSTONE_DISTRICT_ID = os.getenv("WHETSTONE_DISTRICT_ID")
WHETSTONE_USERS_IMPORT_FILE = os.getenv("WHETSTONE_USERS_IMPORT_FILE")
WHETSTONE_OBSVGRPS_IMPORT_FILE = os.getenv("WHETSTONE_OBSVGRPS_IMPORT_FILE")

WHETSTONE_CLIENT_CREDENTIALS = (WHETSTONE_CLIENT_ID, WHETSTONE_CLIENT_SECRET)


def main():
    ws = whetstone.Whetstone()
    ws.authorize_client(client_credentials=WHETSTONE_CLIENT_CREDENTIALS)
    ws.authorize_frontend(
        district_id=WHETSTONE_DISTRICT_ID,
        username=WHETSTONE_USERNAME,
        password=WHETSTONE_PASSWORD,
    )

    # load import users
    with open(WHETSTONE_USERS_IMPORT_FILE) as f:
        import_users = json.load(f)

    new_users = []
    for u in import_users:
        # skip if inactive and already archived
        if u["inactive"] and u["inactive_ws"] and u["archived_at"]:
            continue

        print(f"{u['user_name']} ({u['user_internal_id']})")

        # get IDs
        user_id = u["user_id"]

        # restore
        if not u["inactive"] and u["archived_at"]:
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
            "roles": json.loads(u["role_id"]),
        }

        # create or update
        try:
            if not user_id:
                create_resp = ws.post("users", body=user_payload)

                user_id = create_resp.get("_id")
                u["user_id"] = user_id

                new_users.append(u)
                print("\tCreated")
            else:
                ws.put("users", user_id, body=user_payload)
        except Exception as xc:
            print(xc)
            print(traceback.format_exc())
            continue

        # archive
        if u["inactive"] and not u["archived_at"]:
            ws.delete("users", user_id)
            print("\tArchived")
            continue

    print("Processing school observation group changes...")
    with open(WHETSTONE_OBSVGRPS_IMPORT_FILE) as f:
        import_obsvgrps = json.load(f)

    for s in import_obsvgrps:
        obsvgrps_payload = json.loads(s["observation_groups_dict"])
        obsvgrps_payload["district"] = WHETSTONE_DISTRICT_ID
        for nu in new_users:
            if nu["school_id"] == s["school_id"]:
                og_match = next(
                    iter(
                        [
                            og
                            for og in obsvgrps_payload["observationGroups"]
                            if nu["group_name"] == og["name"]
                        ]
                    ),
                    {},
                )
                role_user_ids = og_match.get(nu["group_type"])
                role_user_ids.append(nu["user_id"])
                print(
                    f"\tAdded {nu['user_name']} to {nu['group_name']} as {nu['group_type']}"
                )

        ws.put("schools", record_id=s["school_id"], body=obsvgrps_payload)


if __name__ == "__main__":
    try:
        main()
    except Exception as xc:
        print(xc)
        print(traceback.format_exc())
