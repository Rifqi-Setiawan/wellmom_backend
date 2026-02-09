
import sys
import os
import logging
from unittest.mock import MagicMock

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

# Mock firebase_admin before importing app.main to prevent connection attempts
sys.modules["firebase_admin"] = MagicMock()
sys.modules["firebase_admin.credentials"] = MagicMock()
sys.modules["firebase_admin.messaging"] = MagicMock()

# Also patch the service initialize method to avoid any logic running
from app.services.firebase_service import firebase_service
firebase_service.initialize = MagicMock(return_value=True)

from fastapi.testclient import TestClient
from app.main import app
from app.api import deps
from app.models.user import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock User and Database
def override_get_current_active_user():
    user = User()
    user.id = 1
    user.email = "test@example.com"
    user.phone = "+6281234567890"
    user.full_name = "Test User"
    user.role = "ibu_hamil"
    user.is_active = True
    user.fcm_token = "old_token"
    return user

def override_get_db():
    try:
        yield None 
    except Exception:
        pass

# Override dependencies
app.dependency_overrides[deps.get_current_active_user] = override_get_current_active_user
app.dependency_overrides[deps.get_db] = override_get_db

client = TestClient(app)

def test_fcm_token_update_put():
    print("\n--- Testing PUT /api/v1/users/me/fcm-token ---")
    try:
        response = client.put(
            "/api/v1/users/me/fcm-token",
            json={"fcm_token": "new_test_token_123"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 405:
            print("❌ FAIL: Got 405 Method Not Allowed.")
        elif response.status_code in [200, 500]:
            print("✅ SUCCESS (Routing): Method is allowed.")
        else:
            print(f"⚠️  WARNING: Unexpected status code {response.status_code}")
    except Exception as e:
        print(f"Error during PUT request: {e}")

def test_fcm_token_update_patch():
    print("\n--- Testing PATCH /api/v1/users/me/fcm-token ---")
    try:
        response = client.patch(
            "/api/v1/users/me/fcm-token",
            json={"fcm_token": "new_test_token_123_patch"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error during PATCH request: {e}")

if __name__ == "__main__":
    test_fcm_token_update_put()
    test_fcm_token_update_patch()
