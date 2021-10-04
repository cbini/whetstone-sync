import json
import os
import traceback

import whetstone
from dotenv import load_dotenv

load_dotenv()

WHETSTONE_CLIENT_ID = os.getenv("WHETSTONE_CLIENT_ID")
WHETSTONE_CLIENT_SECRET = os.getenv("WHETSTONE_CLIENT_SECRET")
WHETSTONE_DISTRICT_ID = os.getenv("WHETSTONE_DISTRICT_ID")
WHETSTONE_USERS_IMPORT_FILE = os.getenv("WHETSTONE_USERS_IMPORT_FILE")

WHETSTONE_CLIENT_CREDENTIALS = (WHETSTONE_CLIENT_ID, WHETSTONE_CLIENT_SECRET)


def main():
    ws = whetstone.Whetstone()
    ws.authorize_client(client_credentials=WHETSTONE_CLIENT_CREDENTIALS)

    # load import users
    with open(WHETSTONE_USERS_IMPORT_FILE) as f:
        import_users = json.load(f)

    print("Syncing users...")
    for u in import_users:
        # skip if inactive and already archived
        if u["inactive"] and u["inactive_ws"] and u["archived_at"]:
            continue

        # get IDs
        user_id = u["user_id"]

        # restore
        if not u["inactive"] and u["archived_at"]:
            ws.put(
                "users",
                record_id=f"{user_id}/restore",
                params={"district": WHETSTONE_DISTRICT_ID},
            )
            print(f"\t{u['user_name']} ({u['user_internal_id']}) - REACTIVATED")

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
                print(f"\t{u['user_name']} ({u['user_internal_id']}) - CREATED")
            else:
                ws.put("users", user_id, body=user_payload)
        except Exception as xc:
            print(xc)
            print(traceback.format_exc())
            continue

        # archive
        if u["inactive"] and not u["archived_at"]:
            ws.delete("users", user_id)
            print(f"\t{u['user_name']} ({u['user_internal_id']}) - ARCHIVED")
            continue

    print("\nProcessing school observation group changes...")
    schools = ws.get("schools").get("data")
    for s in schools:
        print(f"\t{s['name']}")
        obsv_grp_payload = {"district": WHETSTONE_DISTRICT_ID, "observationGroups": []}
        school_users = [
            u for u in import_users if u["school_id"] == s["_id"] and not u["inactive"]
        ]
        for grp in s.get("observationGroups"):
            grp_change = False
            grp_users = [su for su in school_users if su["group_name"] == grp["name"]]
            grp_roles = {k: grp[k] for k in grp if k not in ["_id", "name"]}
            grp_update = {"_id": grp["_id"], "name": grp["name"]}
            for role, membership in grp_roles.items():
                mem_ids = [m.get("_id") for m in membership]
                role_users = [gu for gu in grp_users if gu["group_type"] == role]
                for ru in role_users:
                    if not ru["user_id"] in mem_ids:
                        mem_ids.append(ru["user_id"])
                        print(f"\t\tAdded {ru['user_name']} to {grp['name']}/{role}")
                        grp_change = True
                grp_update[role] = mem_ids
            obsv_grp_payload["observationGroups"].append(grp_update)
        if grp_change:
            ws.put("schools", record_id=s["_id"], body=obsv_grp_payload)
        else:
            print("\t\tNo observation group changes")


if __name__ == "__main__":
    try:
        main()
    except Exception as xc:
        print(xc)
        print(traceback.format_exc())
