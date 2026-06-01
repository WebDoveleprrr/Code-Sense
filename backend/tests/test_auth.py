import pytest
import pytest_asyncio
from app.core.auth import create_access_token, create_refresh_token, verify_token
from app.models.user import UserDocument
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

@pytest_asyncio.fixture(autouse=True)
async def init_mock_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.test_db
    await init_beanie(
        database=db,
        document_models=[UserDocument]
    )

@pytest.mark.asyncio
async def test_jwt_token_generation_and_verification():
    user_id = "507f1f77bcf86cd799439011"
    email = "test@example.com"
    
    # 1. Access Token
    access_token = create_access_token(user_id, email)
    assert isinstance(access_token, str)
    
    payload = verify_token(access_token, "access")
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["email"] == email
    assert payload["type"] == "access"
    
    # 2. Refresh Token
    refresh_token = create_refresh_token(user_id)
    assert isinstance(refresh_token, str)
    
    payload_refresh = verify_token(refresh_token, "refresh")
    assert payload_refresh is not None
    assert payload_refresh["sub"] == user_id
    assert payload_refresh["type"] == "refresh"
    
    # 3. Invalid Token Type Verification
    assert verify_token(access_token, "refresh") is None
    assert verify_token(refresh_token, "access") is None

@pytest.mark.asyncio
async def test_user_document_creation():
    email = "new_user@codesense.ai"
    name = "New User"
    
    user = UserDocument(email=email, name=name)
    await user.insert()
    
    db_user = await UserDocument.find_one(UserDocument.email == email)
    assert db_user is not None
    assert db_user.name == name
    
    # Cleanup
    await db_user.delete()
