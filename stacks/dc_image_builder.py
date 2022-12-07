import json
import re
from pathlib import Path

import aws_cdk.aws_iam as iam
import aws_cdk.aws_imagebuilder as image_builder
import yaml
from aws_cdk.aws_ssm import StringParameter
from aws_cdk.core import Construct, Stack, CfnOutput
import aws_cdk.aws_sns as sns


def validate_name(name):
    name = name.replace(".", "-")
    if not re.match(
        r"^[-_A-Za-z-0-9][-_A-Za-z0-9 ]{1,126}[-_A-Za-z-0-9]$", name
    ):
        raise ValueError(f"{name} isn't valid")
    return name


class DCImageBuilder(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        settings = self.load_settings()

        # Make the infrastructure configuration (the type of instance
        # that will build the image)
        infra_config = self.make_infra_config()

        # Make the recipes and images
        for version, image_data in settings[
            "supported_ubuntu_versions"
        ].items():
            recipe = self.make_recipe(version, image_data)

            distribution = self.make_distribution(version, image_data)
            pipeline = image_builder.CfnImagePipeline(
                self,
                validate_name(f"Ubuntu_{version}_Pipeline"),
                name=validate_name(f"ubuntu_{version}"),
                image_recipe_arn=recipe.attr_arn,
                infrastructure_configuration_arn=infra_config.attr_arn,
                distribution_configuration_arn=distribution.attr_arn,
                schedule=image_builder.CfnImagePipeline.ScheduleProperty(
                    pipeline_execution_start_condition="EXPRESSION_MATCH_AND_DEPENDENCY_UPDATES_AVAILABLE",
                    schedule_expression="rate(1 day)",
                ),
            )
            pipeline.add_depends_on(infra_config)

    def load_settings(self):
        file = Path(__file__).parent.parent / "settings.json"
        return json.load(file.open())

    def make_recipe(self, version, image_data):
        base_ami = image_data["base_ami"]
        components_list = []
        for component in image_data["components"]:
            components_list.append(
                {
                    "componentArn": self.make_component(version, component),
                }
            )
        name = validate_name(f"DCBaseImage_ubuntu_{version}")
        return image_builder.CfnImageRecipe(
            self,
            name,
            name=name,
            version=image_data["recipe_version"],
            components=components_list,
            parent_image=base_ami,
        )

    def make_component(self, version, component):

        if component.get("arn"):
            return component.get("arn")

        component_path = Path() / "components" / version / component.get("file")
        component_yaml = yaml.safe_load(component_path.read_text())

        name = f"{component['name']}_{version}".replace(".", "-").replace(
            " ", "-"
        )

        component = image_builder.CfnComponent(
            self,
            component["name"],
            name=name,
            platform="Linux",
            version=component_yaml.pop("component_version"),
            data=yaml.dump(component_yaml),
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

    def make_infra_config(self) -> image_builder.CfnInfrastructureConfiguration:
        """
        https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-infra-config.html

        Infrastructure configurations specify the Amazon EC2 infrastructure
        that Image Builder uses to build and test your EC2 Image Builder image

        :param instance_profile:
        :return:
        """

        # Make the profile that will be used by the image builder for this
        # instance
        instance_profile = self.make_instance_profile()

        topic = sns.Topic(
            self,
            "dc-wide-image-builds",
            display_name="DC Wide Image Builds",
            topic_name="dc-wide-image-builds"
        )
        self._topic_arn = topic.topic_arn


        infraconfig = image_builder.CfnInfrastructureConfiguration(
            self,
            "DCBaseImageInfraConfig",
            name="DCBaseImageInfraConfig",
            instance_types=["t3.xlarge"],
            instance_profile_name="DCBaseImageInstanceProfile",
            sns_topic_arn=topic.topic_arn
        )

        # infrastructure need to wait for instance profile
        # to complete before beginning deployment.
        infraconfig.add_depends_on(instance_profile)
        return infraconfig

    @property
    def topic_arn(self):
        return self._topic_arn

    def make_distribution(self, version, image_data):
        org_id = StringParameter.value_for_string_parameter(
            self, "OrganisationID"
        )
        dist_name = validate_name(f"Ubuntu-{version}-distribution")
        return image_builder.CfnDistributionConfiguration(
            self,
            dist_name,
            name=dist_name,
            distributions=[
                image_builder.CfnDistributionConfiguration.DistributionProperty(
                    region="eu-west-2",
                    ami_distribution_configuration=image_builder.CfnDistributionConfiguration.AmiDistributionConfigurationProperty(
                        ami_tags={"ubuntu_version": version},
                        launch_permission_configuration=image_builder.CfnDistributionConfiguration.LaunchPermissionConfigurationProperty(
                            organization_arns=[org_id],
                        ),
                    ),
                )
            ],
        )
