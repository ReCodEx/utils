from recodex import client_factory
import recodex.om as om
import sys
import csv


if __name__ == "__main__":
    group_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not group_id:
        print("Usage: {} <group_id>".format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    client = client_factory.get_client_from_session()
    groups = om.Group.load_all(filter_by=om.Group.filter_factory_has_ancestor(group_id))

    ids = set()
    for group in groups:
        students = group.get("privateData", "students") or []
        ids.update(students)

    students = om.User.load_by_ids(list(ids))
    students.sort(key=lambda s: s.get_name(surname_first=True))
    external_keys = set()
    for student in students:
        external = student.get("privateData", "externalIds") or {}
        external_keys.update(external.keys())
    external_keys = sorted(external_keys)

    # print the students in CSV format
    writer = csv.writer(sys.stdout)
    writer.writerow(["id", "last_name", "first_name", "email"] + external_keys)
    for student in students:
        row = [
            student.id(),
            student.get("name", "lastName") or "",
            student.get("name", "firstName") or "",
            student.get("privateData", "email") or "",
        ]
        external = student.get("privateData", "externalIds") or {}
        for key in external_keys:
            row.append(external.get(key, ""))
        writer.writerow(row)
