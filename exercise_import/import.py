import click
import requests
import re
import logging
import yaml
from bs4 import BeautifulSoup
from pathlib import Path
from html2text import html2text
from functools import partial

class Config:
    def __init__(self, api_url, api_token, locale, extension_to_runtime):
        self.api_url = api_url
        self.api_token = api_token
        self.locale = locale
        self.extension_to_runtime = extension_to_runtime

    @classmethod
    def load(cls, config_path):
        config = {
            "extension_to_runtime": {
                "cs": "mono46",
                "c": "c-gcc-linux",
                "pas": "freepascal-linux",
                "java": "java8",
                "cpp": "cxx11-gcc-linux"
            },
            "locale": "cs"
        }

        data = yaml.load(config_path.open("r"))
        config.update(data)

        return cls(**config)

def load_content(exercise_folder):
    content = (Path(exercise_folder) / "content.xml").read_bytes()
    return BeautifulSoup(content, "lxml")

def extract_payload(response):
    json = response.json()
    if not json["success"]:
        raise RuntimeError("Received error from API: " + json["msg"])

    return json["payload"]

def post_request(api_url, headers, url, files={}, data={}):
    response = requests.post(api_url + "/v1/" + url, files=files, data=data, headers=headers)
    return extract_payload(response)

def load_details(soup):
    result = {}

    result["name"] = soup.select("data name")[0].get_text()
    result["version"] = soup.find("exercise")["version"]
    result["description"] = soup.select("data comment")[0].get_text()
    result["difficulty"] = "easy"
    result["isPublic"] = True
    result["isLocked"] = True

    return result

def load_active_text(soup):
    text_entry = soup.select("text[active=1]")[0]
    content = text_entry.find("content").get_text()

    return text_entry["id"], html2text(content)

def load_additional_files(exercise_folder, text_id):
    path = Path(exercise_folder) / "texts" / text_id
    return list(path.glob("*"))

def replace_file_references(text, url_map):
    """
    >>> replace_file_references("[link]($DIR/foo.zip)", {"foo.zip": "https://my.web.com/archive.zip"})
    '[link](https://my.web.com/archive.zip)'
    >>> replace_file_references("![kitten]($DIR/foo.jpg)", {"foo.jpg": "https://my.web.com/image.jpg"})
    '![kitten](https://my.web.com/image.jpg)'
    """

    def replace(match):
        filename = match.group(1)
        return "({})".format(url_map.get(filename, ""))

    return re.sub(r'\(\$DIR/(.*)\)', replace, text)


def load_reference_solution_details(content_soup, extension_to_runtime):
    for solution in content_soup.select("solution"):
        yield solution["id"], {
            "note": solution.find("comment").get_text(),
            "runtimeEnvironmentId": extension_to_runtime[solution.find("extension").get_text()]
        }

def load_reference_solution_file(solution_id, content_soup, exercise_folder):
    extension = content_soup.select("solution[id={}] extension".format(solution_id))[0].get_text()
    return Path(exercise_folder) / "solutions" / solution_id / "source.{}".format(extension)

def load_exercise_files(exercise_folder):
    path = Path(exercise_folder) / "testdata"
    for file_node in path.iterdir():
        if file_node.name == "config":
            continue
        if file_node.suffix in (".in", ".out") and file_node.is_dir():
            for child in file_node.iterdir():
                yield "{}.{}".format(child.stem, file_node.name), child
        else:
            yield file_node.name, file_node

def upload_file(post, path, filename=None):
        filename = filename or path.name
        logging.info("Uploading {}".format(filename) if filename is None else "Uploading {} as {}".format(path.name, filename))

        payload = post("/uploaded-files", files={filename: path.open("rb")})
        uploaded_file_id = payload["id"]

        logging.info("Uploaded with id %s", uploaded_file_id)

        return uploaded_file_id

@click.group()
def cli():
    pass

@cli.command()
@click.argument("exercise_folder")
def details(exercise_folder):
    soup = load_content(exercise_folder)
    print(load_details(soup))
    print(load_active_text(soup))

@cli.command()
@click.argument("exercise_folder")
@click.argument("group_id")
def run(exercise_folder, group_id):
    logging.basicConfig(level=logging.INFO)

    config = Config.load(Path.cwd() / "import-config.yml")
    logging.info("Configuration loaded")

    post = partial(post_request, config.api_url, {"Authorization": "Bearer " + config.api_token})

    content_soup = load_content(exercise_folder)
    logging.info("content.xml loaded")

    # Create a new, empty exercise
    creation_payload = post("/exercises", data={
        "groupId": group_id
    })

    exercise_id = creation_payload["id"]
    logging.info("Exercise created with id %s", exercise_id)

    # Upload additional files (attachments) and associate them with the exercise
    text_id, text = load_active_text(content_soup)
    id_map = {}

    logging.info("Uploading attachments")
    for path in load_additional_files(exercise_folder, text_id):
        id_map[path.name] = upload_file(post, path)

    if id_map:
        post("/exercises/{}/additional-files".format(exercise_id), data={
            "files[{}]".format(i): file_id for i, file_id in enumerate(id_map.values())
        })

    logging.info("Uploaded attachments associated with the exercise")

    # Prepare the exercise text
    url_map = {filename: "{}/v1/uploaded-files/{}/download".format(config.api_url, file_id) for filename, file_id in id_map.items()}
    text = replace_file_references(text, url_map)

    # Set the details of the new exercise
    details = load_details(content_soup)
    details["localizedTexts[0][locale]"] = config.locale
    details["localizedTexts[0][text]"] = text
    post('/exercises/{}'.format(exercise_id), data=details)

    logging.info("Exercise details updated")

    # Upload exercise files and associate them with the exercise
    exercise_files = set()

    logging.info("Uploading supplementary exercise files")
    for name, path in load_exercise_files(exercise_folder):
        exercise_files.add(upload_file(post, path, name))

    post("/exercises/{}/supplementary-files".format(exercise_id), data={
        "files[{}]".format(i): file_id for i, file_id in enumerate(exercise_files)
    })

    logging.info("Uploaded exercise files associated with the exercise")

    # Upload reference solutions
    for solution_id, solution in load_reference_solution_details(content_soup, config.extension_to_runtime):
        path = load_reference_solution_file(solution_id, content_soup, exercise_folder)
        solution["files[0]"] = upload_file(post, path)
        payload = post('/reference-solutions/exercise/{}'.format(exercise_id), data=solution)

        logging.info("New reference solution created, with id %s", payload["id"])

    # Configure tests
    # TODO


if __name__ == '__main__':
    cli()

