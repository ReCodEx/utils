#!/usr/bin/env python3

import git
import os
import sys
import glob
#from copr.v3 import BuildProxy
#from copr.v3.exceptions import CoprRequestException


def die(msg):
    print("ERROR: {}".format(msg))
    sys.exit(1)


def get_version():
    argv = sys.argv
    if len(argv) != 2:
        die("One argument required - version")
    arg = argv[1]

    if len(arg) < 5:
        die("Wrong version format - too short")

    items = arg.split(".")
    if len(items) != 3:
        die("Wrong version format - not semantic version")

    for i in items:
        try:
            int(i)
        except:
            die("Wrong version format - one or more parts are not a number")

    return arg


def get_repo(path=None):
    if path is None:
        path = os.getcwd()
    return git.Repo(path, search_parent_directories=True)


def update_spec_file(spec_file, hexsha, version):
    with open(spec_file, "r+") as f:
        content = f.readlines()
        f.seek(0)
        for line in content:
            if line.startswith("%define unmangled_version"):
                f.write("%define unmangled_version {}\n".format(hexsha))
            elif line.startswith("%define version"):
                f.write("%define version {}\n".format(version))
            elif line.startswith("%define release"):
                f.write("%define release 1\n")
            else:
                f.write(line)


def commit_spec_file(repo, spec_file, version):
    repo.index.add([spec_file])
    repo.index.commit("#! v{}".format(version))
    repo.remotes.origin.push()


def create_tag(repo, version):
    new_tag = repo.create_tag("v{}".format(version), message="Automatic release of version {}".format(version))
    repo.remotes.origin.push(new_tag)


#def build_in_copr(spec_file):
#    build_proxy = BuildProxy.create_from_config_file()
#    #print(build_proxy.get_list("semai", "ReCodEx"))
#
#    endpoint = "/build/create/upload"
#    f = open(spec_file, "rb")
#    data = {
#        "ownername": "semai",
#        "projectname": "ReCodEx",
#    }
#    files = {
#        "pkgs": (os.path.basename(f.name), f, "text/x-rpm-spec"),
#    }
#    try:
#        result = build_proxy._create(endpoint, data, files=files, buildopts=None)
#    except CoprRequestException as ex:
#        print(type(ex.result.__response__))
#        print(ex.result.__response__)
#        print(ex.result.__response__.status_code)
#        print(ex.result.__response__.headers)
#
#    result = build_proxy.create_from_file("semai", "ReCodEx", spec_file)
#    print(result)

def get_changelog(repo):
    tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
    start_tag = tags[-1]
    if len(tags) > 1:
        revisions = "{}...{}".format(start_tag, tags[-2])
    else:
        revisions = start_tag

    commits = repo.iter_commits(revisions)
    lines = []
    for commit in commits:
        lines.append("{} {}".format(commit.hexsha, commit.summary))
    body_commits = "\n".join(lines)
    return "### Changelog\n-\n\n### Commits\n{}".format(body_commits)

def main():
    print('Release script started')

    version = get_version()
    print("- will release version: {}".format(version))

    try:
        repo = get_repo()
        print("- found Git repository in {}".format(repo.working_tree_dir))

        if repo.is_dirty():
            die("repository is dirty")
        print("- repository is clean")

        if repo.active_branch.name != "master":
            die("you cannot make release from branch {}".format(repo.active_branch.name))
        print("- active is master branch")

        commit = repo.active_branch.commit
        print("- current commit: {} ({})".format(commit.hexsha, commit.summary))

        spec_files = glob.glob(os.path.join(repo.working_tree_dir, "*.spec"))
        use_copr = len(spec_files) == 1
        if use_copr:
            spec_file = spec_files[0]
            print("- got SPEC file: {}".format(spec_file))

            update_spec_file(spec_file, commit.hexsha, version)
            print("- SPEC file {} updated".format(spec_file))

            commit_spec_file(repo, spec_file, version)
            print("- repo commited")

        else:
            print("- no exactly one *.spec file found, skipping build")

        create_tag(repo, version)
        print("- tag created")

        # if use_copr:
        #     print("- creating COPR builds")
        #     build_in_copr(spec_file)
        #     print("- COPR builds created")

        print("Finished! The project is successfully released")

        print("\nGenerated changelog:\n--------------------\n")
        changelog = get_changelog(repo)
        print(changelog)

    except Exception as e:
        die("type: {}, data: {}".format(type(e).__name__, str(e)))


if __name__ == '__main__':
    main()

