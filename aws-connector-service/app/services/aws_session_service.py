from typing import Optional

import boto3
from botocore.exceptions import ClientError


def assume_role(role_arn: str, external_id: str, region: Optional[str] = None) -> dict:
    if not external_id:
        raise ValueError("ExternalId is required for role assumption")

    if region:
        sts = boto3.client("sts", region_name=region)
    else:
        sts = boto3.client("sts")

    try:
        response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName="copilot-session",
            ExternalId=external_id,
        )
    except ClientError as exc:
        raise RuntimeError(str(exc)) from exc

    return response["Credentials"]
