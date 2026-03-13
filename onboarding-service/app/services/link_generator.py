import os
from urllib.parse import urlencode

DEFAULT_CLOUDFORMATION_BASE_URL = (
    "https://console.aws.amazon.com/cloudformation/home#/stacks/create/review"
)
DEFAULT_TEMPLATE_URL = (
    "https://yourdomain.com/templates/devops-copilot-onboarding.yaml"
)
DEFAULT_STACK_NAME = "DevOpsCopilotStack"
DEFAULT_PLATFORM_ACCOUNT_ID = "111111111111"


def generate_onboarding_link(external_id: str) -> str:
    cloudformation_base_url = os.getenv(
        "CLOUDFORMATION_BASE_URL", DEFAULT_CLOUDFORMATION_BASE_URL
    )
    template_url = os.getenv("TEMPLATE_URL", DEFAULT_TEMPLATE_URL)
    stack_name = os.getenv("STACK_NAME", DEFAULT_STACK_NAME)
    platform_account_id = os.getenv(
        "PLATFORM_ACCOUNT_ID", DEFAULT_PLATFORM_ACCOUNT_ID
    )
    params = {
        "templateURL": template_url,
        "stackName": stack_name,
        "param_ExternalId": external_id,
        "param_PlatformAccountId": platform_account_id,
    }
    return f"{cloudformation_base_url}?{urlencode(params)}"
