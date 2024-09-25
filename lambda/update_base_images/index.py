import json
from dataclasses import dataclass

import requests
import semver
from github import open_pull_request


@dataclass
class AMIImage:
    region: str
    version_name: str
    version: str
    arch: str
    instance_type: str
    release: str
    ami_link: str
    aki_id: str

    def version_matched(self, other_version):
        return self.version.startswith(other_version)

    @property
    def ami_id(self):
        return str(self.ami_link.split(">")[1].split("<")[0])


def get_current_settings():
    req = requests.get(
        "https://raw.githubusercontent.com/DemocracyClub/dc_image_builder/main/settings.json"
    )
    req.raise_for_status()
    return req.json()


def get_ami_image_data():
    res = requests.get("https://cloud-images.ubuntu.com/locator/ec2/releasesTable")
    res.raise_for_status()
    fixed_json = res.text.replace(""",\n]\n}""", "]}")
    images = []
    for image_json in json.loads(fixed_json)["aaData"]:
        images.append(AMIImage(*image_json))
    return images


def get_latest_image_for_version(version, image_data, region="eu-west-2", arch="amd64"):
    for image in image_data:
        if (
            image.version_matched(version)
            and image.region == region
            and image.arch == arch
        ):
            return image
    raise ValueError(f"No image found for {version=}, {region=}, {arch=}")


def bump_recipe_version(version):
    ver = semver.VersionInfo.parse(version)
    ver.bump_patch()
    return str(ver)


def handler(event, context):
    settings: dict = get_current_settings()
    ami_data = get_ami_image_data()
    for version, image_data in settings["supported_ubuntu_versions"].items():
        latest_image = get_latest_image_for_version(version, ami_data)
        if latest_image.ami_id != image_data["base_ami"]:
            # We have ourselves a new image
            new_settings = settings.copy()
            version_data = new_settings["supported_ubuntu_versions"][version]
            version_data["base_ami"] = latest_image.ami_id
            version_data["recipe_version"] = bump_recipe_version(
                version_data["recipe_version"]
            )
            new_settings["supported_ubuntu_versions"][version] = version_data
            open_pull_request(version, new_settings)


if __name__ == "__main__":
    handler(None, None)
