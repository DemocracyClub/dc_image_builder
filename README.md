# DC base image builder

This project is designed to make AMIs that can be used across DC's products.

There are a few aims:

1. To make a set of base AMIs for different OSs we want. At the time of 
   writing we only use Ubuntu images, but over time we upgrade the Ubuntu 
   version we use. The base images should help us know what version of 
   Ubuntu we're on. The scope of the 
   base image should be quite small. We can install commonly used packages, 
   but application-level logic should be kept in the application image 
   building process.
2. To share components we use when making other images. The AWS image 
   builder platform includes a concept of "components". These are basically 
   small scripts that are run by image builder pipelines. It's possible to 
   create these outside of an image recipe and allow them to be shared 
   across accounts. An example, we might have a shared component for 
   creating an application user. This wouldn't be in the base image, but 
   could be used by image builder in the application account. 


## Creating and updating components

### Background 
Components are stored in `components/[image_version]/`. They are YAML files 
in the [AWS Task Orchestrator and Executor (AWSTOE)](https://docs.aws.amazon.com/imagebuilder/latest/userguide/toe-get-started.html)
format.

This project has added a single key, `component_version` to the [base schema](https://docs.aws.amazon.com/imagebuilder/latest/userguide/toe-use-documents.html#document-schema).

To explain this schema change: each component needs a semver formatted 
version string when it's created in AWS.

The version has to be unique with the file hash, so any changes to the file 
require a new version. This is an excellent guardrail, but without storing 
the version in the document it's hard to know when it needs to be changed.

For example, someone could update the component but not the version. Then 
someone else can bump the version (in a different bit of code). Unless you 
know how the other bit of code related to the YAML on disk, it's hard to 
know what has changed and when.

Adding the version to the YAML file means the change to the component is 
coupled to the version semver.

### Changing an existing component

1. Make the edits you need to the YAML file
2. Update the `component_version` semver according to https://semver.org/
3. Update the semver of the recipe that uses this component (you only need 
   to do this once per edit of the set of components. For example, you could 
   edit 4 components using steps 1 and 2, and only make a single semver 
   change to the recipe)
4. Commit with a useful explanation of the change(s) made
5. Push, and CI/CD should take care of the deployment 


# CI / CD / Deployment

This project uses CircleCI to:

1. Lint and check the code on all commits
2. Run `cdk synth` on commits
3. Run `cdk deploy` on commits to the `main` branch

`cdk synth` requires a valid AWS account in order to run. There is an [open 
feature request](https://github.com/aws/aws-cdk/issues/17066) about this.

## IAM permissions

CDK needs to be bootstrapped in a new account before it can run.

To do this, run `cdk bootstrap` with your privileged developer or admin
account on the AWS account you're settings up. This is a one-time operation,
so only needed if you're setting up a new deployment.

After the bootstrap, CDK needs AWS credentials that have the following:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:AssumeRole"
      ],
      "Resource": [
        "arn:aws:iam::*:role/cdk-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:*"
      ],
      "Resource": "*"
    }
  ]
}
```

**WARNING**: The CDK roles have the `AdministratorAccess` policy attached.
This means that CDK has full admin to the AWS account. Don't use the
CDK user credentials anywhere that shouldn't have full admin access.
