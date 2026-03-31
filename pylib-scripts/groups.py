from recodex import client_factory
import recodex.om as om


def print_group(group, level=0):
    '''
    Print the group and all its children, recursively.
    The level parameter is used to determine the indentation.
    '''
    admins = [admin.get_name() for admin in group.get_admins()]
    admins.sort()
    admin_names = "   [admins: " + ", ".join(admins) + "]" if admins else ""
    if not group.get("organizational"):
        students = "   (students: " + str(len(group.get("privateData", "students") or [])) + ")"
    else:
        students = ""
    print("  " * level + group.get_name() + admin_names + students)

    children = group.get_children()
    children.sort(key=lambda g: g.get_name())
    for child in children:
        print_group(child, level + 1)


if __name__ == "__main__":
    client = client_factory.get_client_from_session()
    roots = om.Group.load_all(filter_by=om.Group.filter_root)
    for root in roots:
        print_group(root)
