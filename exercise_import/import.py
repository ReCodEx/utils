import click
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from html2text import html2text

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

def load_additional_files(exercise_folder):
    pass

def load_reference_solutions(exercise_folder):
    pass

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

    creation_request = request_template.prepare()
    creation_request.url += "/exercises"
    response = session.send(creation_request)
    exercise_id = extract_payload(response)["id"]

    details_request = request_template.prepare()
    details_request.url += '/exercises/{}'.format(exercise_id)
    details_request.files = load_details(content_soup)
    response = session.send(details_request)
    extract_payload(response)


if __name__ == '__main__':
    cli()

