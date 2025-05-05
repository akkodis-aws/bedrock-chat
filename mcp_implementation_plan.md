# MCP Tool Implementation Plan

## Overview
This document outlines a detailed implementation plan for integrating the Model Context Protocol (MCP) tool into Bedrock Chat. The implementation will adhere to the MCP specification (https://modelcontextprotocol.io/specification/2025-03-26) and support Server-Sent Events (SSE) transport only.

## Technical Components

### 1. Backend Implementation

#### MCP Client (`mcp_client.py`)
- Create an async client that implements the MCP specification
- Support SSE transport for streaming responses
- Handle OAuth authentication flows
- Implement error handling and logging

#### MCP Tool Integration (`mcp_tool.py`)
- Extend the existing `AgentTool` class to create an `MCPTool` class
- Support streaming capabilities for real-time responses
- Implement proper result formatting compatible with the existing tool result models
- Add configuration management for MCP providers

#### Configuration Management (`mcp_config.py`)
- Create schema definitions for MCP provider configurations
- Implement storage and retrieval of configurations
- Support both global (admin-only) and per-user configurations
- Add validation for configuration settings

#### OAuth Implementation (`mcp_oauth.py`)
- Implement OAuth 2.0 flow support
- Create secure token storage mechanisms
- Support token refresh functionality
- Add token verification and validation

### 2. API Endpoints

#### Management Endpoints
- `POST /api/mcp/providers` - Add a new MCP provider configuration
- `GET /api/mcp/providers` - List available MCP providers
- `GET /api/mcp/providers/{provider_id}` - Get details about a specific provider
- `PUT /api/mcp/providers/{provider_id}` - Update a provider configuration
- `DELETE /api/mcp/providers/{provider_id}` - Remove a provider configuration

#### OAuth Endpoints
- `GET /api/mcp/auth/{provider_id}` - Initiate OAuth flow
- `GET /api/mcp/auth/{provider_id}/callback` - OAuth callback endpoint
- `DELETE /api/mcp/auth/{provider_id}/revoke` - Revoke OAuth tokens

#### Tool Endpoints
- `POST /api/tools/mcp` - Direct invocation endpoint for the MCP tool (for testing)

### 3. Frontend Implementation

#### Admin Configuration UI (`/admin/mcp`)
- Provider management interface
- Global configuration settings
- Access control for admin-only features

#### User Configuration UI (`/settings/mcp`)
- User-specific provider configuration
- OAuth authorization management
- MCP provider selection and preferences

## Implementation Phases

### Phase 1: Core MCP Client
- Implement basic MCP client following the specification
- Add SSE transport support
- Create initial schema definitions
- Add basic error handling

### Phase 2: Tool Integration
- Implement `MCPTool` class
- Add integration with existing tool system
- Implement result formatting
- Create initial configuration models

### Phase 3: Configuration Management
- Add provider configuration storage
- Implement admin vs. user distinction
- Create management API endpoints
- Add validation and error handling

### Phase 4: OAuth Implementation
- Implement OAuth flow
- Add token storage and management
- Create OAuth endpoints
- Add token refresh mechanisms

### Phase 5: Frontend Development
- Create admin configuration interface
- Build user configuration components
- Implement OAuth flow UI
- Add provider selection interface

### Phase 6: Testing and Documentation
- Write comprehensive tests
- Create documentation for developers
- Add user guides
- Perform security review

## Database Schema

### MCP Provider Configuration Table
```
mcp_providers
- id (UUID, primary key)
- name (string)
- description (text)
- endpoint_url (string)
- is_global (boolean)
- created_at (timestamp)
- updated_at (timestamp)
- created_by (UUID, foreign key to users)
```

### MCP OAuth Configuration Table
```
mcp_oauth_configs
- id (UUID, primary key)
- provider_id (UUID, foreign key to mcp_providers)
- client_id (string)
- client_secret (string, encrypted)
- auth_url (string)
- token_url (string)
- redirect_uri (string)
- scopes (string array)
```

### MCP User Tokens Table
```
mcp_user_tokens
- id (UUID, primary key)
- user_id (UUID, foreign key to users)
- provider_id (UUID, foreign key to mcp_providers)
- access_token (string, encrypted)
- refresh_token (string, encrypted)
- expires_at (timestamp)
- created_at (timestamp)
- updated_at (timestamp)
```

## Security Considerations

1. **Token Storage**: OAuth tokens must be encrypted in the database
2. **Client Secret Management**: Provider client secrets must be secured
3. **Access Control**: Enforce strict permissions for admin configurations
4. **Input Validation**: Validate all inputs to prevent injection attacks
5. **Rate Limiting**: Implement rate limiting for MCP API requests

## Next Steps

1. Review MCP specification to ensure full compliance
2. Create a detailed task breakdown for each phase
3. Start implementation with the core MCP client
4. Set up testing infrastructure for the MCP tool