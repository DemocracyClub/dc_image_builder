import json
import re
from pathlib import Path

from aws_cdk.core import Stack, Construct
import aws_cdk.aws_imagebuilder as image_builder
import aws_cdk.aws_iam as iam


def validate_name(name):
    name = name.replace(".", "-")
    if not re.match(r"^[-_A-Za-z-0-9][-_A-Za-z0-9 ]{1,126}[-_A-Za-z-0-9]$", name):
        raise ValueError(f"{name} isn't valid")
    return name


class DCImageBuilder(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        settings = self.load_settings()

        # Make the instance profile
        instance_profile = self.make_instance_profile()

        # Make the infrastructure configuration
        infra_config = self.make_infra_config(instance_profile)

        # Make the recipes and images
        for version, image_data in settings["supported_ubuntu_versions"].items():
            recipe = self.make_recipe(version, image_data)

            pipeline = image_builder.CfnImagePipeline(
                self,
                validate_name(f"Ubuntu_{version}_Pipeline"),
                name=validate_name(f"ubuntu_{version}"),
                image_recipe_arn=recipe.attr_arn,
                infrastructure_configuration_arn=infra_config.attr_arn,
            )
            pipeline.add_depends_on(infra_config)

    def load_settings(self):
        file = Path(__file__).parent.parent / "settings.json"
        return json.load(file.open())

    def make_recipe(self, version, image_data):
        base_ami = image_data["base_ami"]
        components_list = []
        for component_name, component_file in image_data["components"].items():
            components_list.append(
                {
                    "componentArn": self.make_component(
                        version, component_name, component_file
                    ),
                }
            )
        name = validate_name(f"DCBaseImage_ubuntu_{version}")
        return image_builder.CfnImageRecipe(
            self,
            name,
            name=name,
            version="0.0.1",
            components=components_list,
            parent_image=base_ami,
        )

    def make_component(self, version, name, file):
        component_path = Path() / "components" / version / file
        name = f"{name}_{version}".replace(".", "-").replace(" ", "-")
        component = image_builder.CfnComponent(
            self,
            name,
            name=name,
            platform="Linux",
            version="0.0.1",
            data=component_path.read_text(),
        )
        return component.attr_arn

    def make_instance_profile(self):
        role = iam.Role(
            self,
            "DCBaseImageRole",
            role_name="DCBaseImageRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
        )
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            )
        )
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "EC2InstanceProfileForImageBuilder"
            )
        )

        # create an instance profile to attach the role
        instanceprofile = iam.CfnInstanceProfile(
            self,
            "DCBaseImageInstanceProfile",
            instance_profile_name="DCBaseImageInstanceProfile",
            roles=["DCBaseImageRole"],
        )
        return instanceprofile

    def make_infra_config(self, instance_profile):
        infraconfig = image_builder.CfnInfrastructureConfiguration(
            self,
            "DCBaseImageInfraConfig",
            name="DCBaseImageInfraConfig",
            instance_types=["t3.xlarge"],
            instance_profile_name="DCBaseImageInstanceProfile",
        )

        # infrastructure need to wait for instance profile to complete before beginning deployment.
        infraconfig.add_depends_on(instance_profile)
        return infraconfig
