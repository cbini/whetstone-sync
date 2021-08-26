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
WHETSTONE_IMPORT_FILE = os.getenv("WHETSTONE_IMPORT_FILE")

WHETSTONE_CLIENT_CREDENTIALS = (WHETSTONE_CLIENT_ID, WHETSTONE_CLIENT_SECRET)


# def get_record(data, key, match_value):
#     return next(
#         iter([d for d in data if d.get(key) == match_value and d.get(key) != ""]), {}
#     )


def main():
    ws = whetstone.Whetstone()
    ws.authorize_client(client_credentials=WHETSTONE_CLIENT_CREDENTIALS)
    ws.authorize_frontend(
        district_id=WHETSTONE_DISTRICT_ID,
        username=WHETSTONE_USERNAME,
        password=WHETSTONE_PASSWORD,
    )

    # # pull current data
    # schools = ws.get("schools").get("data")

    # load import users
    with open(WHETSTONE_IMPORT_FILE) as f:
        import_users = json.load(f)

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
                print("\tCreated")
            else:
                ws.put("users", user_id, body=user_payload)
        except Exception as xc:
            print(xc)
            print(traceback.format_exc())
            continue

        # # cue up observation group changes
        # school = get_record(schools, "_id", u["school_id"])
        # if school:
        #     school_obsv_grps = school.get("observationGroups", [])
        #     obsv_grp = get_record(school_obsv_grps, "name", u["group_name"])
        #     obsv_grp_role = obsv_grp.get(u["group_type"], [])
        #     obsv_grp_mem = get_record(obsv_grp_role, "_id", user_id)
        #     if not obsv_grp_mem:
        #         print(f"\tAdded to {u['group_name']} as {u['group_type']}")
        #         obsv_grp_role.append(
        #             {"_id": user_id, "email": u["user_email"], "name": u["user_name"]}
        #         )

        # archive
        if u["inactive"] and not u["archivedAt"]:
            ws.delete("users", user_id)
            print("\tArchived")
            continue

    # print("Processing school observation group changes...")
    # for s in schools:
    #     print(f"{s['name']}")
    #     obsv_grps = s["observationGroups"]
    #     for og in obsv_grps:
    #         observees = [i.get("_id") for i in og.get("observees", [])]
    #         observers = [i.get("_id") for i in og.get("observers", [])]
    #         admins = [i.get("_id") for i in og.get("admins", [])]
    #     print()


if __name__ == "__main__":
    try:
        main()
    except Exception as xc:
        print(xc)
        print(traceback.format_exc())
