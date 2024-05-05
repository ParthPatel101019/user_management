import pytest

from app.models.user_model import UserRole
from app.services.user_service import UserService

pytestmark = pytest.mark.asyncio

SKIP = 0
LIMIT = 100


# * Search


async def test_no_search_query(db_session, search_users):
    search_query = {}
    filter_query = {}

    expected = await UserService.search_users(
        db_session, search_query, filter_query, SKIP, LIMIT
    )

    assert expected == search_users


async def test_with_search_query(db_session, search_users):
    search_query = {"email": "merc.com"}
    filter_query = {}

    expected = await UserService.search_users(
        db_session, search_query, filter_query, SKIP, LIMIT
    )
    actual = [user for user in search_users if "merc.com" in user.email]

    assert expected == actual


async def test_with_search_query_multiple(db_session, search_users):
    search_query = {"email": "merc.com", "role": "MANAGER"}
    filter_query = {}

    expected = await UserService.search_users(
        db_session, search_query, filter_query, SKIP, LIMIT
    )
    actual = [
        user
        for user in search_users
        if "merc.com" in user.email or user.role == UserRole.MANAGER
    ]

    assert expected == actual


async def test_with_search_query_invalid_keys(db_session, search_users):
    search_query = {"email2": "merc.com", "role2": "MANAGER"}
    filter_query = {}

    expected = await UserService.search_users(
        db_session, search_query, filter_query, SKIP, LIMIT
    )
    actual = search_users
    assert expected == actual


async def test_with_search_query_invalid_values(db_session, search_users):
    search_query = {"email": "xyzzz"}
    filter_query = {}

    expected = await UserService.search_users(
        db_session, search_query, filter_query, SKIP, LIMIT
    )
    actual = []
    assert expected == actual


# * Filter


async def test_no_filter_query(db_session, search_users):
    search_query = {}
    filter_query = {}

    expected = await UserService.search_users(
        db_session, search_query, filter_query, SKIP, LIMIT
    )

    assert expected == search_users


async def test_with_filter_query(db_session, search_users):
    search_query = {}
    filter_query = {"is_locked": True}

    expected = await UserService.search_users(
        db_session, search_query, filter_query, SKIP, LIMIT
    )

    actual = [user for user in search_users if user.is_locked is True]

    assert expected == actual


async def test_with_filter_query_multiple(db_session, search_users):
    search_query = {}
    filter_query = {"is_locked": True, "email_verified": False}

    expected = await UserService.search_users(
        db_session, search_query, filter_query, SKIP, LIMIT
    )

    actual = [
        user
        for user in search_users
        if user.is_locked is True and user.email_verified is False
    ]

    assert expected == actual


async def test_with_filter_query_invalid_keys(db_session, search_users):
    search_query = {}
    filter_query = {"is_working": True}

    expected = await UserService.search_users(
        db_session, search_query, filter_query, SKIP, LIMIT
    )
    actual = search_users
    assert expected == actual


async def test_with_filter_query_invalid_values(db_session, search_users):
    search_query = {}
    filter_query = {"email_verified": "abcd"}

    expected = await UserService.search_users(
        db_session, search_query, filter_query, SKIP, LIMIT
    )
    actual = []
    assert expected == actual


async def test_with_search_and_filter_query(db_session, search_users):
    search_query = {"email": "merc.com"}
    filter_query = {"email_verified": True}

    expected = await UserService.search_users(
        db_session, search_query, filter_query, SKIP, LIMIT
    )
    actual = [
        user
        for user in search_users
        if "merc.com" in user.email and user.email_verified is True
    ]
    assert expected == actual
