import logging
from datetime import datetime
from typing import Optional

from app.dependencies import check_admin
from app.repositories.user import (
    list_users,
    get_user_with_groups,
    enable_user,
    disable_user,
    reset_user_password,
)
from app.routes.schemas.admin import (
    UserInfo,
    UserGroupInfo,
    UserListResponse,
    UserStatusUpdateRequest,
    UserPasswordResetRequest,
    UserPasswordResetResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])


def _convert_cognito_user_to_user_info(user_data):
    """
    Convert Cognito user data to UserInfo schema
    """
    # Extract user attributes
    attributes = user_data.get("UserAttributes", [])
    email = next((attr["Value"] for attr in attributes if attr["Name"] == "email"), "")
    
    # Extract user status
    enabled = user_data.get("Enabled", False)
    
    # Extract timestamps
    created_at = user_data.get("UserCreateDate", "").strftime("%Y-%m-%d %H:%M:%S") if user_data.get("UserCreateDate") else ""
    last_modified = user_data.get("UserLastModifiedDate", "").strftime("%Y-%m-%d %H:%M:%S") if user_data.get("UserLastModifiedDate") else ""
    
    # Extract groups
    groups = []
    if "Groups" in user_data:
        groups = [
            UserGroupInfo(
                name=group.get("GroupName", ""),
                description=group.get("Description", "")
            )
            for group in user_data["Groups"]
        ]
    
    return UserInfo(
        id=user_data.get("Username", ""),
        email=email,
        enabled=enabled,
        created_at=created_at,
        last_modified=last_modified,
        groups=groups
    )


@router.get("/admin/users", response_model=UserListResponse)
async def get_users(
    limit: int = Query(50, ge=1, le=100),
    next_token: Optional[str] = None,
    admin_check=Depends(check_admin),
):
    """
    Get all users with pagination support.
    
    This endpoint is restricted to admin users only.
    """
    try:
        users_data, pagination_token = list_users(limit=limit, pagination_token=next_token)
        
        # Convert to UserInfo objects
        user_infos = []
        for user_data in users_data:
            try:
                user_info = _convert_cognito_user_to_user_info(user_data)
                user_infos.append(user_info)
            except Exception as e:
                logger.error(f"Error converting user data: {e}")
                # Continue with other users if one fails
                continue
        
        return UserListResponse(
            users=user_infos,
            next_token=pagination_token
        )
    
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve users: {str(e)}")


@router.get("/admin/users/{user_id}", response_model=UserInfo)
async def get_user(
    user_id: str,
    admin_check=Depends(check_admin),
):
    """
    Get detailed information about a specific user.
    
    This endpoint is restricted to admin users only.
    """
    try:
        user_data = get_user_with_groups(user_id)
        return _convert_cognito_user_to_user_info(user_data)
    
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        if "UserNotFoundException" in str(e):
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user: {str(e)}")


@router.patch("/admin/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    status_update: UserStatusUpdateRequest,
    admin_check=Depends(check_admin),
):
    """
    Enable or disable a user.
    
    This endpoint is restricted to admin users only.
    """
    try:
        if status_update.enabled:
            enable_user(user_id)
            return {"success": True, "message": f"User {user_id} has been enabled"}
        else:
            disable_user(user_id)
            return {"success": True, "message": f"User {user_id} has been disabled"}
    
    except Exception as e:
        logger.error(f"Error updating status for user {user_id}: {e}")
        if "UserNotFoundException" in str(e):
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        raise HTTPException(status_code=500, detail=f"Failed to update user status: {str(e)}")


@router.post("/admin/users/{user_id}/reset-password", response_model=UserPasswordResetResponse)
async def reset_password(
    user_id: str,
    password_reset: UserPasswordResetRequest,
    admin_check=Depends(check_admin),
):
    """
    Reset a user's password.
    
    This endpoint is restricted to admin users only.
    """
    try:
        reset_user_password(user_id, password_reset.temporary_password)
        return UserPasswordResetResponse(
            success=True,
            message=f"Password for user {user_id} has been reset. User will be required to change password on next login."
        )
    
    except Exception as e:
        logger.error(f"Error resetting password for user {user_id}: {e}")
        if "UserNotFoundException" in str(e):
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        if "InvalidPasswordException" in str(e):
            raise HTTPException(status_code=400, detail=f"Invalid password: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reset password: {str(e)}")