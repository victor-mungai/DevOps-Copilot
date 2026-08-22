import os
from typing import Optional

import boto3


def assume_role(role_arn: str, external_id: str, region: Optional[str] = None) -> dict:
    if not external_id:
        raise ValueError("ExternalId is required for role assumption")

    region_name = region or os.getenv("AWS_REGION")
    if region_name:
        sts = boto3.client("sts", region_name=region_name)
    else:
        sts = boto3.client("sts")

    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="copilot-session",
        ExternalId=external_id,
    )

    creds = response["Credentials"]
    assumed_sts = boto3.client(
        "sts",
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=region_name,
    )
    identity = assumed_sts.get_caller_identity()

    return {
        **creds,
        "AssumedAccountId": identity["Account"],
        "AssumedArn": identity["Arn"],
    }
