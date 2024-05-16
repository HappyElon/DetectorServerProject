import logging
import secrets
from typing import Annotated

from fastapi.security import HTTPBasicCredentials, HTTPBasic
from fastapi import Depends, HTTPException
from starlette import status
from starlette.exceptions import WebSocketException

from src.app.containers import async_prop

logger = logging.getLogger("app_logger")


async def authenticate_user_over_http(
        credentials: Annotated[HTTPBasicCredentials, Depends(HTTPBasic())]
):
    logger.info("Http authorization attempt. Login: %s", credentials.username)
    if not await check_user_credentials(credentials):
        logger.info("Http authorization error. Login: %s", credentials.username)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"}
        )


async def authenticate_user_over_ws(
        credentials: Annotated[HTTPBasicCredentials, Depends(HTTPBasic())],
):
    logger.info("WebSocket authorization attempt. Login: %s", credentials.username)
    if not await check_user_credentials(credentials):
        logger.info("WebSocket authorization error. Login: %s", credentials.username)

        raise WebSocketException(code=1002, reason="Incorrect username or password")


async def check_user_credentials(credentials: HTTPBasicCredentials) -> bool:
    credentials_config = await async_prop("auth.credentials")

    correct_username_bytes = bytes(credentials_config.get("login"), "utf-8")
    current_username_bytes = credentials.username.encode("utf8")

    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )

    correct_password_bytes = bytes(credentials_config.get("password"), "utf-8")
    current_password_bytes = credentials.password.encode("utf8")

    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    return is_correct_username and is_correct_password
