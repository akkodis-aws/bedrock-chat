from typing import Literal, List, Optional

from app.routes.schemas.base import BaseSchema
from app.routes.schemas.bot import Knowledge, type_sync_status
from app.repositories.custom_bot import type_shared_scope
from pydantic import Field, EmailStr


class PublishedBotOutput(BaseSchema):
    id: str = Field(..., description="bot_id")
    title: str
    description: str
    published_stack_name: str | None
    published_datetime: int | None
    owner_user_id: str
    shared_scope: type_shared_scope
    shared_status: str


class PublishedBotOutputsWithNextToken(BaseSchema):
    bots: list[PublishedBotOutput]
    next_token: str | None


class UsagePerBotOutput(BaseSchema):
    id: str = Field(..., description="bot_id")
    title: str
    description: str
    is_published: bool
    published_datetime: int | None
    shared_scope: type_shared_scope
    shared_status: str
    owner_user_id: str
    # model_id: str
    total_price: float


class UsagePerUserOutput(BaseSchema):
    id: str = Field(..., description="user_id")
    email: str
    total_price: float


class PublicBotOutput(BaseSchema):
    id: str
    title: str
    instruction: str
    description: str
    create_time: float
    last_used_time: float
    owner_user_id: str
    knowledge: Knowledge
    sync_status: type_sync_status
    sync_status_reason: str
    sync_last_exec_id: str
    shared_scope: type_shared_scope
    shared_status: str
    allowed_cognito_groups: list[str]
    allowed_cognito_users: list[str]


class PushBotInputPinned(BaseSchema):
    to_pinned: Literal[True]
    order: int


class PushBotInputUnpinned(BaseSchema):
    to_pinned: Literal[False]


PushBotInput = PushBotInputPinned | PushBotInputUnpinned


# User Management Schemas

class UserGroupInfo(BaseSchema):
    """Schema for user group information"""
    name: str
    description: str = ""


class UserInfo(BaseSchema):
    """Schema for user information"""
    id: str = Field(..., description="User ID (username in Cognito)")
    email: EmailStr
    enabled: bool
    created_at: str
    last_modified: str
    groups: List[UserGroupInfo] = []


class UserListResponse(BaseSchema):
    """Response schema for listing users"""
    users: List[UserInfo]
    next_token: Optional[str] = None


class UserStatusUpdateRequest(BaseSchema):
    """Request schema for updating user status"""
    enabled: bool


class UserPasswordResetRequest(BaseSchema):
    """Request schema for resetting user password"""
    temporary_password: str = Field(
        ..., 
        description="Temporary password to set for the user",
        min_length=8
    )


class UserPasswordResetResponse(BaseSchema):
    """Response schema for password reset operation"""
    success: bool
    message: str
