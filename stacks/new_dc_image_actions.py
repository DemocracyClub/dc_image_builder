import aws_cdk.aws_sns as sns
from aws_cdk import (
    aws_events_targets,
    aws_lambda,
    aws_lambda_python,
    core,
)
from aws_cdk.aws_ssm import StringParameter
from aws_cdk.core import Construct, Stack


class NewDCImageActions(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, topic_arn, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        GITHUB_USERNAME = StringParameter.value_for_string_parameter(
            self, "BOT_GITHUB_USERNAME"
        )
        GITHUB_EMAIL = StringParameter.value_for_string_parameter(
            self, "BOT_GITHUB_EMAIL"
        )
        GITHUB_API_KEY = StringParameter.value_for_string_parameter(
            self, "BOT_GITHUB_API_KEY"
        )

        new_dc_base_ami_actions = aws_lambda_python.PythonFunction(
            self,
            "new_dc_base_ami_actions",
            function_name="new_dc_base_ami_actions",
            entry="./lambda/new_dc_base_ami_actions/",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            environment={
                "GITHUB_USERNAME": GITHUB_USERNAME,
                "GITHUB_EMAIL": GITHUB_EMAIL,
                "GITHUB_API_KEY": GITHUB_API_KEY,
            },
            timeout=core.Duration.minutes(2),
        )
        aws_events_targets.LambdaFunction(
            handler=new_dc_base_ami_actions,
        )

        sns.Subscription(
            self,
            "listen_for_base_images",
            topic=sns.Topic.from_topic_arn(self, topic_arn=topic_arn, id="topic_arn"),
            endpoint=new_dc_base_ami_actions.function_arn,
            protocol=sns.SubscriptionProtocol.LAMBDA,
        )
