import json
import os
import traceback

import whetstone

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
        if not user_id:
            try:
                create_resp = ws.post("users", body=user_payload)

                user_id = create_resp.get("_id")
                u["user_id"] = user_id

                print(f"\t{u['user_name']} ({u['user_internal_id']}) - CREATED")
            except Exception as xc:
                print(xc)
                print(traceback.format_exc())
                continue
        else:
            try:
                ws.put("users", user_id, body=user_payload)
                print(f"\t{u['user_name']} ({u['user_internal_id']}) - UPDATED")
            except Exception as xc:
                print(xc)
                print(traceback.format_exc())
                continue

        # archive
        if u["inactive"] and not u["archived_at"]:
            ws.delete("users", user_id)
            print(f"\t{u['user_name']} ({u['user_internal_id']}) - ARCHIVED")
            continue

    print("\nProcessing school role changes...")
    schools = ws.get("schools").get("data")
    for s in schools:
        print(f"\t{s['name']}")
        schools_payload = {"district": WHETSTONE_DISTRICT_ID, "observationGroups": []}
        school_users = [
            u
            for u in import_users
            if u["school_id"] == s["_id"] and u["user_id"] and not u["inactive"]
        ]

        # observation groups
        for grp in s.get("observationGroups"):
            role_change = False
            grp_users = [su for su in school_users if su["group_name"] == grp["name"]]
            grp_roles = {k: grp[k] for k in grp if k not in ["_id", "name"]}
            grp_update = {"_id": grp["_id"], "name": grp["name"]}
            for role, membership in grp_roles.items():
                mem_ids = [m.get("_id") for m in membership]
                role_users = [gu for gu in grp_users if role in gu["group_type"]]
                for ru in role_users:
                    if not ru["user_id"] in mem_ids:
                        mem_ids.append(ru["user_id"])
                        print(f"\t\tAdded {ru['user_name']} to {grp['name']}/{role}")
                        role_change = True
                grp_update[role] = mem_ids
            schools_payload["observationGroups"].append(grp_update)

        # school admins
        school_admins = s.get("admins")
        new_school_admins = [
            {"_id": su["user_id"], "name": su["user_name"]}
            for su in school_users
            if "School Admin" in su.get("role_names", [])
        ]
        for nsa in new_school_admins:
            sa_match = [xsa for xsa in school_admins if xsa["_id"] == nsa["_id"]]
            if not sa_match:
                print(f"\t\tAdded {nsa['name']} to School Admins")
                school_admins.append(nsa)
                role_change = True
                schools_payload["admins"] = school_admins

        # school assistant admins
        asst_admins = s.get("assistantAdmins")
        new_asst_admins = [
            {"_id": su["user_id"], "name": su["user_name"]}
            for su in school_users
            if "School Assistant Admin" in su.get("role_names", [])
        ]
        for naa in new_asst_admins:
            sa_match = [xsa for xsa in asst_admins if xsa["_id"] == naa["_id"]]
            if not sa_match:
                print(f"\t\tAdded {naa['name']} to School Assistant Admins")
                asst_admins.append(naa)
                role_change = True
                schools_payload["assistantAdmins"] = asst_admins

        if role_change:
            ws.put("schools", record_id=s["_id"], body=schools_payload)
        else:
            print("\t\tNo school role changes")


if __name__ == "__main__":
    try:
        main()
    except Exception as xc:
        print(xc)
        print(traceback.format_exc())
