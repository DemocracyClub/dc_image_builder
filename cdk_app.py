#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

from stacks.base_image_updater import DCBaseImageUpdater
from stacks.dc_image_builder import DCImageBuilder
from stacks.new_dc_image_actions import NewDCImageActions

app = cdk.App()
image_builder = DCImageBuilder(
    app,
    "DCBaseImageBuilder",
    env=cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region="eu-west-2"),
)

DCBaseImageUpdater(
    app,
    "DCBaseImageUpdater",
    env=cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region="eu-west-2"),
)
NewDCImageActions(
    app,
    "NewDCImageActions",
    topic_arn=image_builder.topic_arn,
    env=cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region="eu-west-2"),
)

app.synth()
