import subprocess
from io import StringIO
import csv
import requests


def set_gravatar(id, gravatar):
    option = "--gravatar" if gravatar else "--no-gravatar"
    subprocess.run(["recodex", "users", "edit", id, option])


def gravatar_exists(url):
    r = requests.get("{}&d=404".format(url))
    return r.status_code == 200


cmd = ["recodex", "users", "search", "--csv", ""]
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
output, errors = proc.communicate()
f = StringIO(output.decode("utf-8"))
reader = csv.reader(f, delimiter=';')
for row in reader:
    id = row[0]
    url = row[5]
    if url is not None and url != "":
        exists = gravatar_exists(url)
        print("{}\t{}\t{}".format(id, url, exists))
        if not exists:
            set_gravatar(id, False)
