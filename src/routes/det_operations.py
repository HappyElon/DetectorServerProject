import json

from io import BytesIO
import uuid

from dependency_injector.wiring import inject, Provide

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Form
from fastapi.security import HTTPBasicCredentials
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.app.security import authenticate_user_over_ws, authenticate_user_over_http

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker

import src.app.utils as utils

import logging

logger = logging.getLogger("app_logger")

router = APIRouter()

authenticate: bool = True  # аутентифицировать ТУЗ
response_on_auth_failed: dict = {
    "data": {},
    "errorCode": 1002,
    "error": 'Authentication failed. Incorrect username or password',
    "ok": False
}
response_on_auth_failed_text: str = json.dumps(response_on_auth_failed)

# База данных
database = utils.g_db_path  # "db/data.db"
# Подключение к базе данных
engine = create_engine(f'sqlite:///{database}')
# Создание фабрики сессий
Session = sessionmaker(bind=engine)


@router.get("/health")
@inject
async def status():
    content = {"data": {"message": "Detector Services Test"}, "errorCode": 0, "ok": True}
    return JSONResponse(content=content)


@router.websocket("/ws/save_result")
@inject
async def save_result(websocket: WebSocket):
    await websocket.accept()

    # Проверка реквизитов
    credentials: dict = await websocket.receive_json()
    await authenticate_user_over_ws(
        HTTPBasicCredentials(
            username=credentials.get("username"),
            password=credentials.get("password")
        )
    )

    try:
        while True:
            # Принимаем конфиг
            res_json = {}
            try:
                message = await websocket.receive_text()
                res_json = json.loads(message)
            except Exception as e:
                logger.error(f"Error on result receiving: {str(e)}")

            # Принимаем файл по частям
            file_content = BytesIO()
            while True:
                try:
                    message = await websocket.receive_bytes()
                    if message == b'':
                        break
                    elif message == b"{'eof' : 1}":
                        break
                    else:
                        file_content.write(message)
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Error on file receiving: {str(e)}")
                    break

            # Id сообщения (контекст процесса)
            message_id = str(uuid.uuid4())

            # Отдаём данные на обработку
            if len(file_content.getvalue()) > 0:
                r = utils.save_result(file_content.getvalue(), res_json, message_id)
                rt = json.dumps(r, ensure_ascii=False)
                if websocket.client_state.CONNECTED:
                    await websocket.send_text(rt)

            if websocket.client_state.DISCONNECTED:
                break
    except WebSocketDisconnect as e:
        logger.warning(f"Websocket disconnected: {str(e)}")


@router.websocket("/ws/create_user")
@inject
async def create_user(websocket: WebSocket):
    await websocket.accept()

    # Проверка реквизитов
    credentials: dict = await websocket.receive_json()
    await authenticate_user_over_ws(
        HTTPBasicCredentials(
            username=credentials.get("username"),
            password=credentials.get("password")
        )
    )

    try:
        while True:
            # Принимаем конфиг
            res_json = {}
            try:
                message = await websocket.receive_text()
                res_json = json.loads(message)
            except Exception as e:
                logger.error(f"Error on result receiving: {str(e)}")

            # Id сообщения (контекст процесса)
            message_id = str(uuid.uuid4())

            # Отдаём данные на обработку
            if len(res_json) > 0:
                r = utils.create_user(res_json, message_id)
                rt = json.dumps(r, ensure_ascii=False)
                if websocket.client_state.CONNECTED:
                    await websocket.send_text(rt)

            if websocket.client_state.DISCONNECTED:
                break
    except WebSocketDisconnect as e:
        logger.warning(f"Websocket disconnected: {str(e)}")


@router.get("/get_results")
@inject
async def get_results(credentials: HTTPBasicCredentials = Depends(authenticate_user_over_http)):
    try:
        with Session() as session:
            # Получаем записи
            sql = text("""
                select id, 
                    class_id, 
                    scrs_timestamp,
                    scrs_path, 
                    is_complete, 
                    result_conf, 
                    result_json, 
                    speed_ms 
                from cv_activity
            """)
            sql_result = session.execute(
                sql,
                {
                }
            )
            rows = list(sql_result)
            result = list()
            for row in rows:
                obj = dict()
                obj["id"], \
                    obj["class_id"], \
                    obj["scrs_timestamp"], \
                    obj["scrs_path"], \
                    obj["is_complete"], \
                    obj["result_conf"], \
                    obj["result_json"], \
                    obj["speed_ms"] = row
                result.append(obj)

            # Формируем результат для передачи
            content = {
                "data": result,
                "errorCode": 0,
                "ok": True
            }
    except Exception as e:
        content = {
            "data": {},
            "errorCode": -1,
            "error": e,
            "ok": False
        }
        logger.debug(f'Error: {e}')
    return JSONResponse(content=content)


@router.get("/get_agr_results")
@inject
async def get_agr_results():
    try:
        with Session() as session:
            # Получаем записи
            sql = text("""
                select date(scrs_timestamp) d,
                    username, 
                    is_complete,
                    count(*) cnt,
                    avg(speed_ms) speed_ms
                from cv_activity
                group by date(scrs_timestamp), username, is_complete
                order by date(scrs_timestamp), username, is_complete
            """)
            sql_result = session.execute(
                sql,
                {
                }
            )
            rows = list(sql_result)
            result = list()
            for row in rows:
                obj = dict()
                obj["d"], \
                    obj["username"], \
                    obj["is_complete"], \
                    obj["cnt"], \
                    obj["speed_ms"] = row
                result.append(obj)

            # Формируем результат для передачи
            content = {
                "data": result,
                "errorCode": 0,
                "ok": True
            }
    except Exception as e:
        content = {
            "data": {},
            "errorCode": -1,
            "error": e,
            "ok": False
        }
        logger.debug(f'Error: {e}')
    return JSONResponse(content=content)


@router.get("/verify_user")
@inject
async def verify_user(userdata, userpassword):
    print(userdata, userpassword)
    return JSONResponse(content=utils.verify_user({"userdata": userdata, "userpassword": userpassword}))
