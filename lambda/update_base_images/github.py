import json
import os
from collections import OrderedDict

from commitment import GitHubClient, GitHubCredentials
from requests import HTTPError


def open_pull_request(version, new_settings):
    branch = f"update-ami-{version}"
    version_settings = new_settings["supported_ubuntu_versions"][version]
    commit_message = f'Update ubuntu_ami_id to {version_settings["base_ami"]}'

    creds = GitHubCredentials(
        repo="DemocracyClub/dc_image_builder",
        name=os.environ["GITHUB_USERNAME"],
        email=os.environ["GITHUB_EMAIL"],
        api_key=os.environ["GITHUB_API_KEY"],
    )
    g = GitHubClient(creds)

    try:
        g.create_branch(branch, base_branch="main")
    except HTTPError as e:
        if e.response.json()["message"] == "Reference already exists":
            print("Branch already exists")
        else:
            raise e

    filename = "settings.json"
    try:
        g.push_file(
            json.dumps(new_settings, indent=2),
            filename,
            commit_message,
            branch=branch,
        )
    except HTTPError:
        pass
    body = f'Found new Ubuntu {version} ({version_settings["base_ami"]})'
    try:
        g.open_pull_request(
            head_branch=branch,
            title=f"Update {version} AMI",
            body=body,
            base_branch="main",
        )
    except HTTPError as e:
        if (
            e.response.json()["errors"][0]["message"]
            == f"A pull request already exists for DemocracyClub:{branch}."
        ):
            print("PR already exists.")
        else:
            raise e
