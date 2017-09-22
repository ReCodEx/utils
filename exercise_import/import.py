import click
import requests
import re
import logging
from bs4 import BeautifulSoup
from pathlib import Path
from html2text import html2text

DEFAULT_LOCALE = "cs"

def load_content(exercise_folder):
    content = (Path(exercise_folder) / "content.xml").read_bytes()
    return BeautifulSoup(content, "lxml")

def extract_payload(response):
    json = response.json()
    if not json["success"]:
        raise RuntimeError("Received error from API: " + json["msg"])

    return json["payload"]

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


def load_reference_solutions(content_soup, exercise_folder):
    pass

def load_exercise_files(exercise_folder):
    path = Path(exercise_folder) / "testdata"
    return list(path.glob("*.in")) + path.glob("*.out")

def upload_file(session, request, path):
        filename = path.name
        logging.info("Uploading %s", filename)

        request.url += "/uploaded-files"
        request.files = {filename: path.read_bytes()}

        response = session.send(request)
        uploaded_file_id = extract_payload(response)["id"]
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
@click.argument("api_url")
@click.argument("api_token")
@click.argument("exercise_folder")
def run(api_url, api_token, exercise_folder):
    session = requests.Session()
    request_template = requests.Request('POST', api_url, headers={"Authorization": "Bearer " + api_token})

    content_soup = load_content(exercise_folder)
    logging.info("content.xml loaded")

    # Create a new, empty exercise
    creation_request = request_template.prepare()
    creation_request.url += "/exercises"
    response = session.send(creation_request)
    exercise_id = extract_payload(response)["id"]
    logging.info("Exercise created with id %s", exercise_id)

    # Upload additional files (attachments) and associate them with the exercise
    text_id, text = load_active_text(content_soup)
    id_map = {}

    logging.info("Uploading attachments")
    for path in load_additional_files(exercise_folder, text_id):
        id_map[path.name] = upload_file(session, request_template.prepare(), path)

    associate_files_request = request_template.prepare()
    associate_files_request.url += "/exercises/{}/additional-files".format(exercise_id)
    associate_files_request.files = {"files[{}]".format(i): file_id for i, file_id in enumerate(id_map.values())}
    extract_payload(session.send(associate_files_request))
    logging.info("Uploaded attachments associated with the exercise")

    # Prepare the exercise text
    url_map = {filename: "{}/uploaded-files/{}/download".format(request_template.url, file_id) for filename, file_id in id_map.items()}
    text = replace_file_references(text, url_map)

    # Set the details of the new exercise
    details_request = request_template.prepare()
    details_request.url += '/exercises/{}'.format(exercise_id)
    details_request.files = load_details(content_soup)
    details_request.files["localizedTexts[0][locale]"] = DEFAULT_LOCALE
    details_request.files["localizedTexts[0][text]"] = text
    response = session.send(details_request)
    extract_payload(response)
    logging.info("Exercise details updated")

    # Upload exercise files and associate them with the exercise
    id_map = {}

    logging.info("Uploading supplementary exercise files")
    for path in load_exercise_files(exercise_folder):
        id_map[path.name] = upload_file(session, request_template.prepare(), path)

    associate_files_request = request_template.prepare()
    associate_files_request.url += "/exercises/{}/supplementary-files".format(exercise_id)
    associate_files_request.files = {"files[{}]".format(i): file_id for i, file_id in enumerate(id_map.values())}
    extract_payload(session.send(associate_files_request))
    logging.info("Uploaded exercise files associated with the exercise")

    # Upload reference solutions
    # TODO

    # Configure tests
    # TODO


if __name__ == '__main__':
    cli()

