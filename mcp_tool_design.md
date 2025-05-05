# MCP Tool Implementation Design

## Overview
This document outlines the design for implementing the Model Context Protocol (MCP) tool in the Bedrock Chat application. The implementation will support:
1. MCP protocol (version from specification 2025-03-26) with Server-Sent Events (SSE) transport
2. OAuth authentication flow for MCP providers
3. DynamoDB storage for OAuth tokens and configuration
4. UI components for both per-user and global (admin-only) tool configuration

## Architecture Components

### 1. Backend Components

#### 1.1 MCP Tool Implementation
Unlike other tools in the system, the MCP tool will need special handling to:
- Support the MCP protocol spec
- Handle OAuth flows
- Store and retrieve OAuth tokens securely
- Support both per-user and global configuration options

```python
# backend/app/agents/tools/mcp_tool.py

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from .agent_tool import AgentTool, ToolFunctionResult
from ...repositories.models.oauth_token import OAuthToken, OAuthTokenRepository
from ...repositories.models.mcp_config import MCPConfig, MCPConfigRepository
# ... more imports

class MCPToolInput(BaseModel):
    query: str = Field(..., description="The query to send to the MCP provider")
    provider_id: str = Field(..., description="The MCP provider to use")
    # ... other input fields

class MCPTool(AgentTool):
    def __init__(self):
        super().__init__(
            name="mcp",
            description="Sends queries to external models via the Model Context Protocol",
            args_schema=MCPToolInput,
            function=self._run_mcp_query
        )
        self.oauth_repository = OAuthTokenRepository()
        self.config_repository = MCPConfigRepository()
    
    async def _run_mcp_query(self, args: MCPToolInput, bot=None, model=None) -> ToolFunctionResult:
        # 1. Get provider configuration
        provider_config = await self.config_repository.get_provider_config(args.provider_id)
        if not provider_config:
            return ToolFunctionResult(
                content="MCP provider not found",
                metadata={"error": "Provider not configured"}
            )
        
        # 2. Get OAuth token if needed
        oauth_token = None
        if provider_config.requires_oauth:
            user_id = bot.user_id if bot else None  # Handle global vs user-specific
            oauth_token = await self.oauth_repository.get_token(args.provider_id, user_id)
            if not oauth_token and provider_config.oauth_required:
                return ToolFunctionResult(
                    content="OAuth authentication required for this MCP provider",
                    metadata={"error": "oauth_required", "provider_id": args.provider_id}
                )
        
        # 3. Create MCP client and send request
        client = MCPClient(
            provider_url=provider_config.endpoint_url,
            oauth_token=oauth_token.access_token if oauth_token else None,
            # ... other client config
        )
        
        try:
            result = await client.send_query(args.query)
            return ToolFunctionResult(
                content=result.content,
                metadata={"provider": args.provider_id}
            )
        except Exception as e:
            return ToolFunctionResult(
                content=f"Error querying MCP provider: {str(e)}",
                metadata={"error": str(e)}
            )
```

#### 1.2 MCP Client Implementation

```python
# backend/app/agents/tools/mcp_client.py

import aiohttp
import json
import asyncio
from typing import Optional, Dict, Any, List

class MCPClient:
    """Client for interacting with MCP-compliant providers using SSE transport"""
    
    def __init__(self, provider_url: str, oauth_token: Optional[str] = None):
        self.provider_url = provider_url
        self.oauth_token = oauth_token
    
    async def send_query(self, query: str) -> Dict[str, Any]:
        """Send a query to the MCP provider and process SSE response"""
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        if self.oauth_token:
            headers["Authorization"] = f"Bearer {self.oauth_token}"
        
        request_body = {
            "prompt": query,
            "transport": "sse"
            # Other MCP parameters as needed
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.provider_url,
                headers=headers,
                json=request_body
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"MCP provider error: {response.status} - {error_text}")
                
                # Process SSE response
                buffer = ""
                result = {"content": ""}
                
                async for line in response.content:
                    line = line.decode('utf-8')
                    if line.startswith('data:'):
                        data = json.loads(line[5:].strip())
                        if data.get('type') == 'content':
                            result['content'] += data.get('content', '')
                        # Process other MCP response types
                
                return result
```

#### 1.3 OAuth Implementation

```python
# backend/app/routes/oauth.py

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from ..repositories.models.oauth_token import OAuthTokenRepository
from ..repositories.models.mcp_config import MCPConfigRepository
from ..user import User
import secrets
import time
# ... more imports

router = APIRouter(prefix="/oauth", tags=["oauth"])

@router.get("/authorize/{provider_id}")
async def authorize(
    provider_id: str,
    request: Request,
    user: User = Depends(get_current_user)
):
    # Generate state parameter to prevent CSRF
    state = secrets.token_urlsafe(32)
    
    # Store state in session
    request.session["oauth_state"] = state
    request.session["oauth_provider"] = provider_id
    
    # Get provider configuration
    config_repo = MCPConfigRepository()
    provider_config = await config_repo.get_provider_config(provider_id)
    
    if not provider_config:
        raise HTTPException(status_code=404, detail="MCP provider not found")
    
    # Build authorization URL
    auth_url = f"{provider_config.oauth_auth_url}?response_type=code&client_id={provider_config.oauth_client_id}"
    auth_url += f"&redirect_uri={request.base_url}oauth/callback"
    auth_url += f"&state={state}"
    auth_url += f"&scope={provider_config.oauth_scope}"
    
    return RedirectResponse(auth_url)

@router.get("/callback")
async def oauth_callback(
    code: str,
    state: str,
    request: Request,
    user: User = Depends(get_current_user)
):
    # Verify state parameter
    stored_state = request.session.get("oauth_state")
    provider_id = request.session.get("oauth_provider")
    
    if not stored_state or not provider_id or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    
    # Clear session data
    del request.session["oauth_state"]
    del request.session["oauth_provider"]
    
    # Get provider configuration
    config_repo = MCPConfigRepository()
    provider_config = await config_repo.get_provider_config(provider_id)
    
    if not provider_config:
        raise HTTPException(status_code=404, detail="MCP provider not found")
    
    # Exchange code for token
    token_data = await exchange_code_for_token(
        code,
        provider_config.oauth_token_url,
        provider_config.oauth_client_id,
        provider_config.oauth_client_secret,
        f"{request.base_url}oauth/callback"
    )
    
    # Store token in DynamoDB
    token_repo = OAuthTokenRepository()
    await token_repo.save_token(
        provider_id=provider_id,
        user_id=user.id,
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        expires_at=int(time.time()) + int(token_data.get("expires_in", 3600)),
        token_type=token_data.get("token_type", "Bearer")
    )
    
    # Redirect to success page
    return RedirectResponse(f"/mcp/success?provider={provider_id}")

async def exchange_code_for_token(
    code: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str
) -> dict:
    """Exchange authorization code for access token"""
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri
            }
        ) as response:
            if response.status != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to exchange code for token: {await response.text()}"
                )
            
            return await response.json()
```

### 2. DynamoDB Data Models

#### 2.1 OAuth Token Model

```python
# backend/app/repositories/models/oauth_token.py

from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import time
from ...repositories.common import get_table
from boto3.dynamodb.conditions import Key

class OAuthToken(BaseModel):
    provider_id: str
    user_id: Optional[str] = None  # None for global tokens
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: int
    token_type: str = "Bearer"
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return time.time() >= self.expires_at

class OAuthTokenRepository:
    def __init__(self):
        self.table = get_table()
    
    async def save_token(
        self,
        provider_id: str,
        user_id: Optional[str],
        access_token: str,
        refresh_token: Optional[str],
        expires_at: int,
        token_type: str = "Bearer"
    ) -> OAuthToken:
        """Save OAuth token to DynamoDB"""
        
        token = OAuthToken(
            provider_id=provider_id,
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            token_type=token_type
        )
        
        # Define DynamoDB keys
        pk = f"OAUTH#{provider_id}"
        sk = f"USER#{user_id}" if user_id else "GLOBAL"
        
        # Save to DynamoDB
        self.table.put_item(
            Item={
                "PK": pk,
                "SK": sk,
                "Type": "OAuthToken",
                "ProviderID": provider_id,
                "UserID": user_id,
                "AccessToken": access_token,
                "RefreshToken": refresh_token,
                "ExpiresAt": expires_at,
                "TokenType": token_type,
                "CreatedAt": int(time.time())
            }
        )
        
        return token
    
    async def get_token(self, provider_id: str, user_id: Optional[str] = None) -> Optional[OAuthToken]:
        """Get OAuth token from DynamoDB"""
        
        # Define DynamoDB keys
        pk = f"OAUTH#{provider_id}"
        sk = f"USER#{user_id}" if user_id else "GLOBAL"
        
        # Query DynamoDB
        response = self.table.get_item(
            Key={
                "PK": pk,
                "SK": sk
            }
        )
        
        item = response.get("Item")
        if not item:
            # If user-specific token not found, try global token
            if user_id:
                return await self.get_token(provider_id)
            return None
        
        # Create token object
        token = OAuthToken(
            provider_id=item["ProviderID"],
            user_id=item.get("UserID"),
            access_token=item["AccessToken"],
            refresh_token=item.get("RefreshToken"),
            expires_at=item["ExpiresAt"],
            token_type=item.get("TokenType", "Bearer")
        )
        
        # Refresh token if expired
        if token.is_expired and token.refresh_token:
            # Implement token refresh logic
            pass
        
        return token
    
    async def delete_token(self, provider_id: str, user_id: Optional[str] = None) -> None:
        """Delete OAuth token from DynamoDB"""
        
        # Define DynamoDB keys
        pk = f"OAUTH#{provider_id}"
        sk = f"USER#{user_id}" if user_id else "GLOBAL"
        
        # Delete from DynamoDB
        self.table.delete_item(
            Key={
                "PK": pk,
                "SK": sk
            }
        )
```

#### 2.2 MCP Provider Configuration Model

```python
# backend/app/repositories/models/mcp_config.py

from typing import Optional, List
from pydantic import BaseModel
from ...repositories.common import get_table
from boto3.dynamodb.conditions import Key
import time

class MCPProviderConfig(BaseModel):
    id: str
    name: str
    description: str
    endpoint_url: str
    is_global: bool = False
    requires_oauth: bool = False
    oauth_required: bool = False  # If True, OAuth is required; if False, it's optional
    oauth_auth_url: Optional[str] = None
    oauth_token_url: Optional[str] = None
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    oauth_scope: Optional[str] = None
    created_by: Optional[str] = None
    created_at: int = 0
    updated_at: int = 0

class MCPConfigRepository:
    def __init__(self):
        self.table = get_table()
    
    async def save_provider_config(self, config: MCPProviderConfig) -> MCPProviderConfig:
        """Save MCP provider configuration to DynamoDB"""
        
        now = int(time.time())
        if config.created_at == 0:
            config.created_at = now
        config.updated_at = now
        
        # Define DynamoDB keys
        pk = f"MCP#CONFIG"
        sk = f"PROVIDER#{config.id}"
        
        # Save to DynamoDB
        self.table.put_item(
            Item={
                "PK": pk,
                "SK": sk,
                "Type": "MCPProviderConfig",
                "ID": config.id,
                "Name": config.name,
                "Description": config.description,
                "EndpointURL": config.endpoint_url,
                "IsGlobal": config.is_global,
                "RequiresOAuth": config.requires_oauth,
                "OAuthRequired": config.oauth_required,
                "OAuthAuthURL": config.oauth_auth_url,
                "OAuthTokenURL": config.oauth_token_url,
                "OAuthClientID": config.oauth_client_id,
                "OAuthClientSecret": config.oauth_client_secret,
                "OAuthScope": config.oauth_scope,
                "CreatedBy": config.created_by,
                "CreatedAt": config.created_at,
                "UpdatedAt": config.updated_at
            }
        )
        
        return config
    
    async def get_provider_config(self, provider_id: str) -> Optional[MCPProviderConfig]:
        """Get MCP provider configuration from DynamoDB"""
        
        # Define DynamoDB keys
        pk = f"MCP#CONFIG"
        sk = f"PROVIDER#{provider_id}"
        
        # Query DynamoDB
        response = self.table.get_item(
            Key={
                "PK": pk,
                "SK": sk
            }
        )
        
        item = response.get("Item")
        if not item:
            return None
        
        # Create config object
        return MCPProviderConfig(
            id=item["ID"],
            name=item["Name"],
            description=item["Description"],
            endpoint_url=item["EndpointURL"],
            is_global=item["IsGlobal"],
            requires_oauth=item["RequiresOAuth"],
            oauth_required=item.get("OAuthRequired", False),
            oauth_auth_url=item.get("OAuthAuthURL"),
            oauth_token_url=item.get("OAuthTokenURL"),
            oauth_client_id=item.get("OAuthClientID"),
            oauth_client_secret=item.get("OAuthClientSecret"),
            oauth_scope=item.get("OAuthScope"),
            created_by=item.get("CreatedBy"),
            created_at=item["CreatedAt"],
            updated_at=item["UpdatedAt"]
        )
    
    async def list_provider_configs(self, user_id: Optional[str] = None) -> List[MCPProviderConfig]:
        """List MCP provider configurations from DynamoDB"""
        
        # Query DynamoDB
        response = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"MCP#CONFIG")
        )
        
        configs = []
        for item in response.get("Items", []):
            # Filter by global or user-specific
            if user_id and not item.get("IsGlobal", False) and item.get("CreatedBy") != user_id:
                continue
                
            configs.append(MCPProviderConfig(
                id=item["ID"],
                name=item["Name"],
                description=item["Description"],
                endpoint_url=item["EndpointURL"],
                is_global=item["IsGlobal"],
                requires_oauth=item["RequiresOAuth"],
                oauth_required=item.get("OAuthRequired", False),
                oauth_auth_url=item.get("OAuthAuthURL"),
                oauth_token_url=item.get("OAuthTokenURL"),
                oauth_client_id=item.get("OAuthClientID"),
                oauth_client_secret=item.get("OAuthClientSecret"),
                oauth_scope=item.get("OAuthScope"),
                created_by=item.get("CreatedBy"),
                created_at=item["CreatedAt"],
                updated_at=item["UpdatedAt"]
            ))
        
        return configs
    
    async def delete_provider_config(self, provider_id: str) -> None:
        """Delete MCP provider configuration from DynamoDB"""
        
        # Define DynamoDB keys
        pk = f"MCP#CONFIG"
        sk = f"PROVIDER#{provider_id}"
        
        # Delete from DynamoDB
        self.table.delete_item(
            Key={
                "PK": pk,
                "SK": sk
            }
        )
```

### 3. Frontend Components

The frontend will need components for:
1. MCP provider configuration (admin only)
2. OAuth authentication flow
3. User-specific MCP provider configuration 
4. UI for using MCP in conversations

Here are the key frontend components:

#### 3.1 Admin MCP Provider Management
Create a React component for administrators to manage MCP providers, including:
- Adding/editing/removing providers
- Configuring OAuth settings
- Setting global vs per-user availability

#### 3.2 User MCP Provider Settings
Create a React component for users to:
- View available MCP providers
- Authenticate with OAuth for providers that require it
- Configure personal settings for MCP providers

#### 3.3 OAuth Callback Handler
Create a React component to handle OAuth redirects and display success/failure messages.

## Implementation Plan

1. **Backend Development**
   - Create DynamoDB models for OAuth tokens and MCP configuration
   - Implement the MCP client with SSE support
   - Implement OAuth flow endpoints
   - Implement the MCP tool class

2. **Frontend Development**
   - Create admin UI for MCP provider management
   - Create user UI for MCP authentication and settings
   - Implement OAuth callback handling

3. **Integration**
   - Register the MCP tool with the agent system
   - Add MCP configuration to the settings UI
   - Test the complete flow

## Testing Approach

1. **Unit Tests**
   - Test MCP client functionality with mock responses
   - Test OAuth token storage and retrieval
   - Test MCP provider configuration management

2. **Integration Tests**
   - Test OAuth flow with mock providers
   - Test MCP tool with mock MCP providers
   - Test UI components with mock API responses

3. **End-to-end Tests**
   - Test complete OAuth flow with real providers
   - Test MCP functionality with real providers
   - Test UI components with real API responses

## Security Considerations

1. **OAuth Token Security**
   - Store OAuth tokens securely in DynamoDB
   - Implement token refresh logic
   - Encrypt sensitive data at rest

2. **Access Control**
   - Enforce proper authorization for MCP provider management
   - Ensure users can only access their own OAuth tokens
   - Validate OAuth state parameter to prevent CSRF attacks

3. **Data Privacy**
   - Ensure user data is properly isolated
   - Implement proper error handling to prevent data leakage
   - Follow AWS best practices for secure DynamoDB access