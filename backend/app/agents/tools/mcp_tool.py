"""
MCP (Model Context Protocol) Tool Implementation

This module implements a tool for Model Context Protocol as defined in 
https://modelcontextprotocol.io/specification/2025-03-26
"""

import logging
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union
import httpx
from pydantic import BaseModel, Field, HttpUrl, validator

from app.repositories.models.conversation import (
    ToolResultModel,
    TextToolResultModel,
    JsonToolResultModel,
)
from app.repositories.models.custom_bot import BotModel
from app.routes.schemas.conversation import type_model_name
from app.agents.tools.agent_tool import AgentTool, ToolFunctionResult

logger = logging.getLogger(__name__)

# Schema definitions for MCP configuration
class MCPOAuthConfig(BaseModel):
    """OAuth configuration for MCP provider"""
    client_id: str = Field(description="OAuth client ID for the MCP provider")
    client_secret: str = Field(description="OAuth client secret for the MCP provider")
    auth_url: HttpUrl = Field(description="OAuth authorization URL")
    token_url: HttpUrl = Field(description="OAuth token URL")
    redirect_uri: HttpUrl = Field(description="Redirect URI for OAuth callback")
    scopes: List[str] = Field(
        default=["read"], 
        description="List of scopes to request during OAuth authorization"
    )

class MCPConfig(BaseModel):
    """Configuration for an MCP provider"""
    name: str = Field(description="Name of the MCP provider")
    description: str = Field(description="Description of the MCP provider")
    endpoint_url: HttpUrl = Field(description="Base URL for the MCP provider API")
    oauth: Optional[MCPOAuthConfig] = Field(
        default=None, 
        description="OAuth configuration if the provider requires authentication"
    )
    global_config: bool = Field(
        default=False, 
        description="Whether this is a global configuration (admin only) or user-specific"
    )

# Schema definition for MCP tool input
class MCPToolInput(BaseModel):
    """Input parameters for the MCP tool"""
    provider_id: str = Field(description="ID of the MCP provider to use")
    query: str = Field(description="Query or request to send to the MCP provider")
    additional_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context or parameters to send to the provider"
    )

# MCP Client implementation
class MCPClient:
    """
    Client for interacting with MCP (Model Context Protocol) providers
    
    Implements the MCP specification from https://modelcontextprotocol.io/specification/2025-03-26
    with support for SSE transport only.
    """
    
    def __init__(self, config: MCPConfig, access_token: Optional[str] = None):
        """
        Initialize the MCP client
        
        Args:
            config: MCPConfig - Configuration for the MCP provider
            access_token: Optional[str] - OAuth access token if available
        """
        self.config = config
        self.access_token = access_token
        
    async def _make_request(self, 
                           endpoint: str, 
                           data: Dict[str, Any],
                           user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Make a request to the MCP provider
        
        Args:
            endpoint: Endpoint path to append to the base URL
            data: Request data to send
            user_id: Optional user ID for per-user configurations
            
        Returns:
            Dict[str, Any]: The response data
        """
        url = f"{self.config.endpoint_url}/{endpoint.lstrip('/')}"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream"  # SSE transport only
        }
        
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
            
        if user_id:
            headers["X-User-ID"] = user_id
            
        try:
            async with httpx.AsyncClient() as client:
                # For SSE streaming we need to handle the response differently
                response = await client.post(
                    url, 
                    json=data,
                    headers=headers,
                    timeout=60.0
                )
                response.raise_for_status()
                
                # Parse SSE stream
                result = await self._parse_sse_stream(response)
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"MCP request failed: {str(e)}")
            raise Exception(f"MCP request failed: {str(e)}")
        
    async def _parse_sse_stream(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Parse Server-Sent Events (SSE) stream from MCP provider
        
        Args:
            response: HTTP response with SSE content
            
        Returns:
            Dict[str, Any]: Aggregated response data
        """
        accumulated_data = []
        metadata = {}
        
        async for line in response.aiter_lines():
            if not line or line.isspace():
                continue
                
            if line.startswith('data: '):
                data_str = line[6:]  # Remove 'data: ' prefix
                try:
                    event_data = json.loads(data_str)
                    if "type" in event_data:
                        if event_data["type"] == "content":
                            # Content event - append to accumulated data
                            accumulated_data.append(event_data.get("content", ""))
                        elif event_data["type"] == "metadata":
                            # Metadata event - store in metadata dict
                            metadata.update(event_data.get("metadata", {}))
                except json.JSONDecodeError:
                    # If it's not JSON, treat as plain text content
                    accumulated_data.append(data_str)
                    
        # Combine accumulated content
        combined_content = "".join(accumulated_data)
        
        return {
            "content": combined_content,
            "metadata": metadata
        }
    
    async def query(self, 
                  query: str, 
                  additional_context: Optional[Dict[str, Any]] = None,
                  user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a query to the MCP provider
        
        Args:
            query: Query text to send
            additional_context: Optional additional context parameters
            user_id: Optional user ID for per-user configurations
            
        Returns:
            Dict[str, Any]: The response from the provider
        """
        data = {
            "query": query
        }
        
        if additional_context:
            data["context"] = additional_context
            
        return await self._make_request("query", data, user_id)

# OAuth token storage
class OAuthTokenStorage:
    """Simple in-memory storage for OAuth tokens"""
    
    def __init__(self):
        self.tokens = {}  # user_id -> {provider_id -> token_info}
        
    def store_token(self, 
                   user_id: str, 
                   provider_id: str, 
                   access_token: str, 
                   refresh_token: Optional[str] = None,
                   expires_at: Optional[datetime] = None):
        """Store a token for a user and provider"""
        if user_id not in self.tokens:
            self.tokens[user_id] = {}
            
        self.tokens[user_id][provider_id] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at
        }
        
    def get_token(self, user_id: str, provider_id: str) -> Optional[Dict[str, Any]]:
        """Get a token for a user and provider"""
        if user_id in self.tokens and provider_id in self.tokens[user_id]:
            return self.tokens[user_id][provider_id]
        return None
    
    def delete_token(self, user_id: str, provider_id: str):
        """Delete a token for a user and provider"""
        if user_id in self.tokens and provider_id in self.tokens[user_id]:
            del self.tokens[user_id][provider_id]

# Global token storage instance
token_storage = OAuthTokenStorage()

# MCP Tool implementation
def _mcp_tool_function(
    args: MCPToolInput,
    bot: Optional[BotModel] = None,
    model_name: Optional[type_model_name] = None,
) -> ToolFunctionResult:
    """
    Execute the MCP tool function
    
    Args:
        args: MCPToolInput - The input parameters for the MCP tool
        bot: Optional[BotModel] - The bot model if available
        model_name: Optional[type_model_name] - The model name if available
        
    Returns:
        ToolFunctionResult - The result of the tool execution
    """
    # This would be implemented to retrieve the MCP config and call the client
    # For now, we'll return a placeholder response
    result = {
        "status": "success",
        "content": f"MCP result for query: {args.query}",
        "provider": args.provider_id
    }
    
    # Return the result as a JsonToolResultModel
    return JsonToolResultModel(
        json_string=json.dumps(result),
        content_for_human=f"Retrieved information from MCP provider '{args.provider_id}':\n{result['content']}"
    )

# Create the MCP tool instance
mcp_tool = AgentTool(
    name="mcp",
    description="Query external information providers through the Model Context Protocol (MCP)",
    args_schema=MCPToolInput,
    function=_mcp_tool_function
)