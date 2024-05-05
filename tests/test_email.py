import pytest


@pytest.mark.asyncio
async def test_send_markdown_email(email_service):
    user_data = {
        "email": "test@example.com",
        "name": "Test User",
        "verification_url": "http://example.com/verify?token=abc123",
    }
    await email_service.send_user_email(user_data, "email_verification")
    # Manual verification in Mailtrap
