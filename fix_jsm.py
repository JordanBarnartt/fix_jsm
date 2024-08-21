import csv

import httpx
from decouple import config

JIRA_URL = "https://uwaterloo.atlassian.net/rest/api/3"
JIRA_USERNAME = config("JIRA_USERNAME")
JIRA_PASSWORD = config("JIRA_PASSWORD")

ISS_API_URL = "https://iss-api.uwaterloo.ca/resolve_upn"
ISS_API_KEY = config("ISS_API_KEY")


def get_email_from_account_id(account_id):
    response = httpx.get(
        JIRA_URL + "/user",
        params={"accountId": account_id},
        auth=(JIRA_USERNAME, JIRA_PASSWORD),
    )
    return response.json()["emailAddress"]


def get_account_id_from_email(email):
    response = httpx.get(
        JIRA_URL + "/user/search",
        params={"query": email},
        auth=(JIRA_USERNAME, JIRA_PASSWORD),
    ).json()
    for user in response:
        if user["accountType"] == "atlassian":
            return user["accountId"]


def get_issues_associated_with_account_id(account_id):
    params = {
        "jql": '"request participants"="{account_id}"',
        "maxResults": 100,
    }
    response = httpx.get(
        JIRA_URL, params=params, auth=(JIRA_USERNAME, JIRA_PASSWORD)
    ).json()
    return response["issues"]


def get_watiam_associated_with_email(email):
    response = httpx.get(
        ISS_API_URL,
        params={"email": email},
        headers={"Authorization": ISS_API_KEY, "Content-Type": "application/json"},
    )
    return response.json()


def replace_account_id(key, old_account_id, new_account_id):
    response = httpx.put(
        JIRA_URL + "/issue/" + key,
        params={"notifyUsers": "false"},
        json={
            "update": {
                "customfield_10026": [
                    {"remove": {"id": old_account_id}},
                    {"add": {"id": new_account_id}},
                ]
            }
        },
        auth=(JIRA_USERNAME, JIRA_PASSWORD),
    )
    return response.json()


with open("jsm.csv", "r") as file:
    reader = csv.reader(file)
    for row in reader:
        old_account_id = row[0]
        email = get_email_from_account_id(old_account_id)
        watiam = get_watiam_associated_with_email(email)
        issues = get_issues_associated_with_account_id(old_account_id)
        new_account_id = get_account_id_from_email(watiam)

        for issue in issues:
            key = issue["key"]
            replace_account_id(key, old_account_id, new_account_id)
