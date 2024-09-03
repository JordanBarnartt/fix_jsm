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
    try:
        return response.json()["emailAddress"]
    except KeyError:
        print(f"Could not find an email associated with {account_id}")
        return None


def get_account_id_from_email(email):
    if email is None:
        return None
    response = httpx.get(
        JIRA_URL + "/user/search",
        params={"query": email},
        auth=(JIRA_USERNAME, JIRA_PASSWORD),
    ).json()
    if not response:
        print(f"Could not find an Atlassian account associated with {email}")
        return None
    for user in response:
        if user["accountType"] == "atlassian":
            return user["accountId"]


def get_issues_associated_with_account_id(account_id):
    params = {
        "jql": f'"request participants"="{account_id}"',
        "maxResults": 100,
    }
    response = httpx.get(
        JIRA_URL + "/search", params=params, auth=(JIRA_USERNAME, JIRA_PASSWORD)
    )
    response_json = response.json()
    return response_json["issues"]


def get_watiam_associated_with_email(email):
    response = httpx.get(
        ISS_API_URL,
        params={"id": email},
        headers={
            "Authorization": f"Token {ISS_API_KEY}",
            "Content-Type": "application/json",
        },
        verify=False,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        print(f"Could not find a WatIAM associated with {email}")
        return
    watiam = response.text
    if not watiam:
        print(f"Could not find a WatIAM associated with {email}")
    return watiam


def replace_account_id(key, old_account_id, new_account_id):
    if new_account_id is None:
        print(f"User does not have an Atlassian account, taking no action on {key}")
        return
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
    response.raise_for_status()


with open("jsm.csv", "r") as file:
    reader = csv.reader(file)
    for row in reader:
        old_account_id = row[0]
        email = get_email_from_account_id(old_account_id)
        if not email:
            continue
        watiam = get_watiam_associated_with_email(email)
        if not watiam:
            continue
        issues = get_issues_associated_with_account_id(old_account_id)
        if not issues:
            print(f"No issues found for {email}")
            continue
        new_account_id = get_account_id_from_email(watiam)
        if new_account_id is None:
            continue

        for issue in issues:
            key = issue["key"]
            replace_account_id(key, old_account_id, new_account_id)
            print(
                f"Replaced {email} ({old_account_id}) with {watiam} ({new_account_id}) in {key}"
            )
