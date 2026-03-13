import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError


def assume_role_and_get_account_id(
    role_arn: str, external_id: str, region: Optional[str] = None
) -> str:
    if not external_id:
        raise ValueError("ExternalId is required for role verification")

    region_name = region or os.getenv("AWS_REGION")
    if region_name:
        sts = boto3.client("sts", region_name=region_name)
    else:
        sts = boto3.client("sts")

    try:
        response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName="copilot-verify",
            ExternalId=external_id,
        )
    except ClientError as exc:
        raise RuntimeError(str(exc)) from exc

    creds = response["Credentials"]
    assumed_sts = boto3.client(
        "sts",
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=region_name,
    )
    identity = assumed_sts.get_caller_identity()
    account_id = identity["Account"]
    return account_id
