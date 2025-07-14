import logging
import os
from typing import Dict, List, Optional, Tuple

import boto3
from app.user import UserGroup, UserWithoutGroups
from botocore.exceptions import ClientError
from reretry import retry

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

USER_POOL_ID = os.environ.get("USER_POOL_ID")

client = boto3.client("cognito-idp")


class TooManyRequestsError(Exception):
    pass


@retry(TooManyRequestsError, tries=3, delay=1)
def find_users_by_email_prefix(prefix: str, limit: int = 10) -> list[UserWithoutGroups]:
    try:
        logger.debug(f"Searching users with email prefix: {prefix}")
        response = client.list_users(
            UserPoolId=USER_POOL_ID, Filter=f'email ^= "{prefix.lower()}"', Limit=limit
        )
        logger.debug(f"Found {len(response['Users'])} users")
        logger.debug(response)

        users = response.get("Users", [])

        converted_users = [
            UserWithoutGroups.from_cognito_idp_response(user) for user in users
        ]
        logger.debug(f"Converted users: {converted_users}")
        return converted_users
    except ClientError as e:
        # Retry if rate limit.
        # The quota is 30 RPS for ListUsers.
        # See: https://docs.aws.amazon.com/cognito/latest/developerguide/quotas.html
        if e.response["Error"]["Code"] == "TooManyRequestsException":
            logger.warning(f"Rate limit exceeded. Retrying... Error: {e}")
            raise TooManyRequestsError()
        else:
            raise


@retry(TooManyRequestsError, tries=3, delay=1)
def find_group_by_name_prefix(prefix: str) -> list[UserGroup]:
    groups = []
    next_token = None
    MAX_ATTEMPTS = 5

    try:
        for _ in range(MAX_ATTEMPTS):
            params = {"UserPoolId": USER_POOL_ID}
            if next_token:
                params["NextToken"] = next_token

            response = client.list_groups(**params)
            groups.extend(response.get("Groups", []))

            next_token = response.get("NextToken")
            if not next_token:
                break

        if next_token:
            logger.warning(
                f"Reached the maximum retrieval attempts ({MAX_ATTEMPTS}). "
                "Some groups might not have been retrieved."
            )

        # Cognito client does not support prefix filtering.
        # So we need to filter the groups on client side.
        filtered_groups = [
            UserGroup.from_cognito_idp_response(group)
            for group in groups
            if group["GroupName"].lower().startswith(prefix.lower())
        ]
        return filtered_groups

    except ClientError as e:
        # Retry if rate limit.
        # The quota is 20 RPS for ListUsers.
        # See: https://docs.aws.amazon.com/cognito/latest/developerguide/quotas.html
        if e.response["Error"]["Code"] == "TooManyRequestsException":
            logger.warning(f"Rate limit exceeded. Retrying... Error: {e}")
            raise TooManyRequestsError()
        else:
            raise


@retry(TooManyRequestsError, tries=3, delay=1)
def find_user_by_id(id: str) -> UserWithoutGroups | None:
    try:
        logger.debug(f"get user with id: {id}")
        response = client.admin_get_user(UserPoolId=USER_POOL_ID, Username=id)
        logger.debug(response)

        converted_user = UserWithoutGroups.from_cognito_idp_response(response)
        logger.debug(f"Converted user: {converted_user}")

        return converted_user
    except ClientError as e:

        # Retry if rate limit.
        # The quota is 120 RPS for AdminGetUser.
        # See: https://docs.aws.amazon.com/cognito/latest/developerguide/quotas.html
        if e.response["Error"]["Code"] == "TooManyRequestsException":
            logger.warning(f"Rate limit exceeded. Retrying... Error: {e}")
            raise TooManyRequestsError()

        if e.response["Error"]["Code"] == "UserNotFoundException":
            logger.warning(f"User Not Found: {e}")
            return None

        else:
            raise


@retry(TooManyRequestsError, tries=3, delay=1)
def list_users(limit: int = 50, pagination_token: Optional[str] = None) -> Tuple[List[Dict], Optional[str]]:
    """
    List all users in the Cognito user pool with pagination support.
    
    Args:
        limit: Maximum number of users to return
        pagination_token: Token for pagination
        
    Returns:
        Tuple containing list of users and next pagination token if available
    """
    try:
        params = {
            "UserPoolId": USER_POOL_ID,
            "Limit": limit
        }
        
        if pagination_token:
            params["PaginationToken"] = pagination_token
            
        response = client.list_users(**params)
        
        return response.get("Users", []), response.get("PaginationToken")
    
    except ClientError as e:
        if e.response["Error"]["Code"] == "TooManyRequestsException":
            logger.warning(f"Rate limit exceeded. Retrying... Error: {e}")
            raise TooManyRequestsError()
        else:
            logger.error(f"Error listing users: {e}")
            raise


@retry(TooManyRequestsError, tries=3, delay=1)
def get_user_with_groups(user_id: str) -> Dict:
    """
    Get detailed user information including group membership.
    
    Args:
        user_id: The user's ID (username in Cognito)
        
    Returns:
        Dictionary containing user details and group membership
    """
    try:
        # Get user details
        user_response = client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=user_id
        )
        
        # Get user groups
        groups_response = client.admin_list_groups_for_user(
            UserPoolId=USER_POOL_ID,
            Username=user_id
        )
        
        # Combine the information
        user_info = user_response
        user_info["Groups"] = groups_response.get("Groups", [])
        
        return user_info
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "TooManyRequestsException":
            logger.warning(f"Rate limit exceeded. Retrying... Error: {e}")
            raise TooManyRequestsError()
        elif e.response["Error"]["Code"] == "UserNotFoundException":
            logger.warning(f"User not found: {user_id}")
            raise
        else:
            logger.error(f"Error getting user details: {e}")
            raise


@retry(TooManyRequestsError, tries=3, delay=1)
def enable_user(user_id: str) -> None:
    """
    Enable a user in the Cognito user pool.
    
    Args:
        user_id: The user's ID (username in Cognito)
    """
    try:
        client.admin_enable_user(
            UserPoolId=USER_POOL_ID,
            Username=user_id
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "TooManyRequestsException":
            logger.warning(f"Rate limit exceeded. Retrying... Error: {e}")
            raise TooManyRequestsError()
        else:
            logger.error(f"Error enabling user: {e}")
            raise


@retry(TooManyRequestsError, tries=3, delay=1)
def disable_user(user_id: str) -> None:
    """
    Disable a user in the Cognito user pool.
    
    Args:
        user_id: The user's ID (username in Cognito)
    """
    try:
        client.admin_disable_user(
            UserPoolId=USER_POOL_ID,
            Username=user_id
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "TooManyRequestsException":
            logger.warning(f"Rate limit exceeded. Retrying... Error: {e}")
            raise TooManyRequestsError()
        else:
            logger.error(f"Error disabling user: {e}")
            raise


@retry(TooManyRequestsError, tries=3, delay=1)
def reset_user_password(user_id: str, temporary_password: str) -> None:
    """
    Reset a user's password in the Cognito user pool.
    
    Args:
        user_id: The user's ID (username in Cognito)
        temporary_password: The temporary password to set
    """
    try:
        client.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=user_id,
            Password=temporary_password,
            Permanent=False  # Force user to change password on next login
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "TooManyRequestsException":
            logger.warning(f"Rate limit exceeded. Retrying... Error: {e}")
            raise TooManyRequestsError()
        else:
            logger.error(f"Error resetting user password: {e}")
            raise


@retry(TooManyRequestsError, tries=3, delay=1)
def get_user_status(user_id: str) -> str:
    """
    Get the status of a user (enabled or disabled).
    
    Args:
        user_id: The user's ID (username in Cognito)
        
    Returns:
        String indicating user status ("ENABLED" or "DISABLED")
    """
    try:
        response = client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=user_id
        )
        return response.get("Enabled", False)
    except ClientError as e:
        if e.response["Error"]["Code"] == "TooManyRequestsException":
            logger.warning(f"Rate limit exceeded. Retrying... Error: {e}")
            raise TooManyRequestsError()
        else:
            logger.error(f"Error getting user status: {e}")
            raise