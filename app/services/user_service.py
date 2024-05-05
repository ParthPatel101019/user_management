from builtins import Exception, bool, classmethod, int, len, str
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import String, and_, cast, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import func

from app.dependencies import get_settings
from app.exceptions.user_exceptions import (
    AccountLockedException,
    EmailAlreadyExistsException,
    InvalidCredentialsException,
    InvalidVerificationTokenException,
    UserNotFoundException,
)
from app.models.user_model import User, UserRole
from app.schemas.user_schemas import UserCreate, UserUpdate
from app.services.db_service import DbService
from app.services.email_service import EmailService
from app.utils.nickname_gen import generate_nickname
from app.utils.security import (
    generate_verification_token,
    hash_password,
    verify_password,
)

settings = get_settings()


class UserService(DbService):  # SQLAlchemy's AsyncSession
    @classmethod
    async def _fetch_user(cls, session: AsyncSession, **filters) -> Optional[User]:
        # TODO SQL
        query = select(User).filter_by(**filters)
        result = await cls._execute_query(session, query)
        return result.scalars().first() if result else None

    @classmethod
    async def get_by_id(cls, session: AsyncSession, user_id: UUID) -> User:
        user = await cls._fetch_user(session, id=user_id)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found.")
        return user

    @classmethod
    async def get_by_nickname(
        cls, session: AsyncSession, nickname: str
    ) -> Optional[User]:
        return await cls._fetch_user(session, nickname=nickname)

    @classmethod
    async def get_by_email(cls, session: AsyncSession, email: str) -> Optional[User]:
        return await cls._fetch_user(session, email=email)

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        user_data: Dict[str, str],
        email_service: EmailService,
    ) -> User:
        try:
            validated_data = UserCreate(**user_data).model_dump()
            existing_user = await cls.get_by_email(session, validated_data["email"])
            if existing_user:
                raise EmailAlreadyExistsException(
                    "User with given email already exists."
                )

            validated_data["hashed_password"] = hash_password(
                validated_data.pop("password")
            )
            new_user = User(**validated_data)
            new_nickname = generate_nickname()
            while await cls.get_by_nickname(session, new_nickname):
                new_nickname = generate_nickname()
            new_user.nickname = new_nickname
            user_count = await cls.count(session)
            new_user.role = UserRole.ADMIN if user_count == 0 else UserRole.ANONYMOUS
            if new_user.role == UserRole.ADMIN:
                new_user.email_verified = True
            else:
                new_user.verification_token = generate_verification_token()

            session.add(new_user)
            await session.commit()
            # TODO Improvement
            if new_user.email_verified == False:
                await email_service.send_verification_email(new_user)
            return new_user
        except ValidationError as e:
            raise e

    @classmethod
    async def update(
        cls, session: AsyncSession, user_id: UUID, update_data: Dict[str, str]
    ) -> User:
        try:
            validated_data = UserUpdate(**update_data).model_dump(exclude_unset=True)
            if "password" in validated_data:
                validated_data["hashed_password"] = hash_password(
                    validated_data.pop("password")
                )
            query = (
                update(User)
                .where(User.id == user_id)
                .values(**validated_data)
                .execution_options(synchronize_session="fetch")
            )
            await cls._execute_query(session, query)
            updated_user = await cls.get_by_id(session, user_id)
            session.refresh(updated_user)
            return updated_user
        except UserNotFoundException as e:
            raise e
        except Exception as e:
            raise e

    @classmethod
    async def delete(cls, session: AsyncSession, user_id: UUID) -> None:
        user = await cls.get_by_id(session, user_id)
        await session.delete(user)
        await session.commit()

    @classmethod
    async def list_users(
        cls, session: AsyncSession, skip: int = 0, limit: int = 10
    ) -> List[User]:
        query = select(User).offset(skip).limit(limit)
        result = await cls._execute_query(session, query)
        return result.scalars().all()

    @classmethod
    async def search_users(
        cls,
        session: AsyncSession,
        search_query: dict,
        filter_query: dict,
        skip: int = 0,
        limit: int = 10,
    ) -> List[User]:
        query = select(User)

        search_conditions = []
        if "email" in search_query:
            search_conditions.append(User.email.like(f"%{search_query['email']}%"))
        if "nickname" in search_query:
            search_conditions.append(
                User.nickname.like(f"%{search_query['nickname']}%")
            )
        if "role" in search_query:
            search_conditions.append(
                cast(User.role, String).like(f"%{search_query['role']}%")
            )
        if "bio" in search_query:
            query = query.filter(
                func.to_tsvector("english", User.bio).match(
                    func.to_tsquery("english", search_query["bio"])
                )
            )

        if search_conditions:
            query = query.filter(or_(*search_conditions))

        filter_conditions = []
        if "is_professional" in filter_query:
            filter_conditions.append(
                User.is_professional == filter_query["is_professional"]
            )
        if "is_locked" in filter_query:
            filter_conditions.append(User.is_locked == filter_query["is_locked"])
        if "email_verified" in filter_query:
            filter_conditions.append(
                User.email_verified == filter_query["email_verified"]
            )
        if "created_at_from" in filter_query and "created_at_to" in filter_query:
            filter_conditions.append(
                User.created_at.between(
                    filter_query["created_at_from"], filter_query["created_at_to"]
                )
            )

        if filter_conditions:
            query = query.filter(and_(*filter_conditions))

        query = query.offset(skip).limit(limit)

        try:
            result = await cls._execute_query(session, query)
            return result.scalars().all()
        except AttributeError:
            return []

    @classmethod
    async def register_user(
        cls,
        session: AsyncSession,
        user_data: Dict[str, str],
        email_service: EmailService,
    ) -> User:
        return await cls.create(session, user_data, email_service)

    @classmethod
    async def login_user(cls, session: AsyncSession, email: str, password: str) -> User:
        user = await cls.get_by_email(session, email)
        if not user:
            raise InvalidCredentialsException("Incorrect email or password.")
        if user.is_locked:
            raise AccountLockedException(
                "Account locked due to too many failed login attempts."
            )
        if not user.email_verified:
            raise InvalidCredentialsException("Email not verified.")
        if not verify_password(password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.max_login_attempts:
                user.is_locked = True
            session.add(user)
            await session.commit()
            raise InvalidCredentialsException("Incorrect email or password.")

        user.reset_login_attempts()
        user.update_last_login()
        session.add(user)
        await session.commit()
        return user

    @classmethod
    async def is_account_locked(cls, session: AsyncSession, email: str) -> bool:
        user = await cls.get_by_email(session, email)
        return user.is_locked if user else False

    @classmethod
    async def reset_password(
        cls, session: AsyncSession, user_id: UUID, new_password: str
    ) -> None:
        hashed_password = hash_password(new_password)
        user = await cls.get_by_id(session, user_id)
        user.hashed_password = hashed_password
        user.failed_login_attempts = 0
        user.is_locked = False
        session.add(user)
        await session.commit()

    @classmethod
    async def verify_email_with_token(
        cls, session: AsyncSession, user_id: UUID, token: str
    ) -> None:
        user = await cls.get_by_id(session, user_id)
        if not user.verification_token or user.verification_token != token:
            raise InvalidVerificationTokenException(
                "Invalid or expired verification token."
            )
        user.email_verified = True
        user.verification_token = None
        user.role = UserRole.AUTHENTICATED
        session.add(user)
        await session.commit()

    @classmethod
    async def count(cls, session: AsyncSession) -> int:
        query = select(User)
        result = await session.execute(query)
        return len(result.scalars().all())

    @classmethod
    async def unlock_user_account(cls, session: AsyncSession, user_id: UUID) -> None:
        user = await cls.get_by_id(session, user_id)
        if not user.is_locked:
            return
        user.is_locked = False
        user.failed_login_attempts = 0
        session.add(user)
        await session.commit()
