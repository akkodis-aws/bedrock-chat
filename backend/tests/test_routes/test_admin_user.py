import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.user import User

client = TestClient(app)


@pytest.fixture
def mock_admin_user():
    return User(
        id="admin_user_id",
        name="admin_user",
        email="admin@example.com",
        groups=["Admin"]
    )


@pytest.fixture
def mock_non_admin_user():
    return User(
        id="non_admin_user_id",
        name="non_admin_user",
        email="user@example.com",
        groups=["CreatingBotAllowed"]
    )


@patch("app.dependencies.get_current_user")
def test_list_users_admin_access(mock_get_current_user, mock_admin_user):
    # Setup
    mock_get_current_user.return_value = mock_admin_user
    
    # Mock the list_users function
    with patch("app.routes.admin_user.list_users") as mock_list_users:
        mock_list_users.return_value = (
            [
                {
                    "Username": "user1",
                    "UserStatus": "CONFIRMED",
                    "Enabled": True,
                    "UserCreateDate": "2023-01-01 00:00:00",
                    "UserLastModifiedDate": "2023-01-02 00:00:00",
                    "UserAttributes": [
                        {"Name": "email", "Value": "user1@example.com"}
                    ]
                },
                {
                    "Username": "user2",
                    "UserStatus": "CONFIRMED",
                    "Enabled": False,
                    "UserCreateDate": "2023-01-03 00:00:00",
                    "UserLastModifiedDate": "2023-01-04 00:00:00",
                    "UserAttributes": [
                        {"Name": "email", "Value": "user2@example.com"}
                    ]
                }
            ],
            "next_token_value"
        )
        
        # Execute
        response = client.get("/admin/users")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert len(data["users"]) == 2
        assert data["next_token"] == "next_token_value"
        assert data["users"][0]["id"] == "user1"
        assert data["users"][0]["email"] == "user1@example.com"
        assert data["users"][0]["enabled"] is True
        assert data["users"][1]["id"] == "user2"
        assert data["users"][1]["email"] == "user2@example.com"
        assert data["users"][1]["enabled"] is False


@patch("app.dependencies.get_current_user")
def test_list_users_non_admin_access(mock_get_current_user, mock_non_admin_user):
    # Setup
    mock_get_current_user.return_value = mock_non_admin_user
    
    # Execute
    response = client.get("/admin/users")
    
    # Assert
    assert response.status_code == 403


@patch("app.dependencies.get_current_user")
def test_get_user_details(mock_get_current_user, mock_admin_user):
    # Setup
    mock_get_current_user.return_value = mock_admin_user
    
    # Mock the get_user_with_groups function
    with patch("app.routes.admin_user.get_user_with_groups") as mock_get_user:
        mock_get_user.return_value = {
            "Username": "test_user",
            "UserStatus": "CONFIRMED",
            "Enabled": True,
            "UserCreateDate": "2023-01-01 00:00:00",
            "UserLastModifiedDate": "2023-01-02 00:00:00",
            "UserAttributes": [
                {"Name": "email", "Value": "test_user@example.com"}
            ],
            "Groups": [
                {"GroupName": "CreatingBotAllowed", "Description": "Can create bots"}
            ]
        }
        
        # Execute
        response = client.get("/admin/users/test_user")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test_user"
        assert data["email"] == "test_user@example.com"
        assert data["enabled"] is True
        assert len(data["groups"]) == 1
        assert data["groups"][0]["name"] == "CreatingBotAllowed"
        assert data["groups"][0]["description"] == "Can create bots"


@patch("app.dependencies.get_current_user")
def test_update_user_status_enable(mock_get_current_user, mock_admin_user):
    # Setup
    mock_get_current_user.return_value = mock_admin_user
    
    # Mock the enable_user function
    with patch("app.routes.admin_user.enable_user") as mock_enable_user:
        mock_enable_user.return_value = None
        
        # Execute
        response = client.patch(
            "/admin/users/test_user/status",
            json={"enabled": True}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "enabled" in data["message"]
        mock_enable_user.assert_called_once_with("test_user")


@patch("app.dependencies.get_current_user")
def test_update_user_status_disable(mock_get_current_user, mock_admin_user):
    # Setup
    mock_get_current_user.return_value = mock_admin_user
    
    # Mock the disable_user function
    with patch("app.routes.admin_user.disable_user") as mock_disable_user:
        mock_disable_user.return_value = None
        
        # Execute
        response = client.patch(
            "/admin/users/test_user/status",
            json={"enabled": False}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "disabled" in data["message"]
        mock_disable_user.assert_called_once_with("test_user")


@patch("app.dependencies.get_current_user")
def test_reset_user_password(mock_get_current_user, mock_admin_user):
    # Setup
    mock_get_current_user.return_value = mock_admin_user
    
    # Mock the reset_user_password function
    with patch("app.routes.admin_user.reset_user_password") as mock_reset_password:
        mock_reset_password.return_value = None
        
        # Execute
        response = client.post(
            "/admin/users/test_user/reset-password",
            json={"temporary_password": "NewTemp123!"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "reset" in data["message"]
        mock_reset_password.assert_called_once_with("test_user", "NewTemp123!")


@patch("app.dependencies.get_current_user")
def test_reset_user_password_invalid(mock_get_current_user, mock_admin_user):
    # Setup
    mock_get_current_user.return_value = mock_admin_user
    
    # Execute - password too short
    response = client.post(
        "/admin/users/test_user/reset-password",
        json={"temporary_password": "short"}
    )
    
    # Assert
    assert response.status_code == 422  # Validation error