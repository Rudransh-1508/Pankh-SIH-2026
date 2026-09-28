import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import InvalidToken, read_access_token
from app.config import Settings, get_settings
from app.db import get_session
from app.models import Official, Student

_bearer = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def current_student(
    session: SessionDep,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Student:
    unauthorised = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Sign in to continue", {"WWW-Authenticate": "Bearer"}
    )
    if credentials is None:
        raise unauthorised
    try:
        student_id: uuid.UUID = read_access_token(settings, credentials.credentials)
    except InvalidToken as error:
        raise unauthorised from error
    student = await session.get(Student, student_id)
    if student is None:
        raise unauthorised
    return student


CurrentStudent = Annotated[Student, Depends(current_student)]


async def current_official(
    session: SessionDep,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Official:
    unauthorised = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Sign in as an official", {"WWW-Authenticate": "Bearer"}
    )
    if credentials is None:
        raise unauthorised
    try:
        official_id = read_access_token(settings, credentials.credentials, role="official")
    except InvalidToken as error:
        raise unauthorised from error
    official = await session.get(Official, official_id)
    if official is None:
        raise unauthorised
    return official


CurrentOfficial = Annotated[Official, Depends(current_official)]
