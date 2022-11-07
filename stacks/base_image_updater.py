from aws_cdk import (
    aws_events,
    aws_events_targets,
    aws_lambda,
    aws_lambda_python,
    core,
)
from aws_cdk.aws_ssm import StringParameter
from aws_cdk.core import Construct, Stack


class DCBaseImageUpdater(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
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

        check_for_updates = aws_lambda_python.PythonFunction(
            self,
            "check_for_updates",
            function_name="check_for_updates",
            entry="./lambda/update_base_images/",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            environment={
                "GITHUB_USERNAME": GITHUB_USERNAME,
                "GITHUB_EMAIL": GITHUB_EMAIL,
                "GITHUB_API_KEY": GITHUB_API_KEY,
            },
            timeout=core.Duration.minutes(1),
        )
        event_lambda_target = aws_events_targets.LambdaFunction(
            handler=check_for_updates
        )

        run_schedule = aws_events.Rule(
            self,
            "update-ami-pr-cron",
            schedule=aws_events.Schedule.rate(core.Duration.days(1)),
            targets=[event_lambda_target],
        )
