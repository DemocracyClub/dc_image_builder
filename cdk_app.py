#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

from stacks.dc_image_builder import DCImageBuilder


app = cdk.App()
DCImageBuilder(
    app,
    "DCBaseImageBuilder",
    env=cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region="eu-west-2"),
)

app.synth()
