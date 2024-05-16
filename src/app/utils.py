# Сервисные функции общего назначения
import os.path
import uuid
from datetime import datetime
from typing import Any

import threading
import yaml

import datetime
import json

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import logging

logger = logging.getLogger("app_logger")

# Создаем объект ThreadLocal для хранения message_id
thread_local = threading.local()

system_level: str = os.getenv('SYSTEMLEVEL', 'DEV')
print(f'System is (prod/demo/test/dev): {system_level}')

# Грузим конфиг --------
config_path = "./resources/config/config.yaml"
if system_level.upper() in ('PROD', 'DEMO', 'TEST'):
    config_path = "./resources/config/config_" + system_level.lower() + ".yaml"

config_yaml: dict
with open(config_path, 'r') as file:
    config_yaml = yaml.safe_load(file)
# ----------------------
# noinspection PyTypeChecker
config: dict = config_yaml


def prop(
        property_path: str,
        default: Any = None,
        config_dict: dict = None
) -> str | dict:
    try:
        key_path = property_path.split(".")
        config_or_property: str | dict = config_dict
        for key in key_path:
            config_or_property = config_or_property.get(key)
        if config_or_property is None:
            config_or_property = default
        return config_or_property
    except Exception as e:
        logger.warning(f'utils.prop: {e}')
        return default


g_app_root: str = prop('app.root', '', config)
g_app_data_root: str = prop('app.dataRoot', '', config)
# БД
g_db_path: str = prop('db.path', '', config)
# 'runs'
g_runs: str = prop('images.runsFolder', '', config)


logger = logging.getLogger("app_logger")

# База данных
database = g_db_path  # "db/data.db"
# Подключение к базе данных
engine = create_engine(f'sqlite:///{database}')
# Создание фабрики сессий
Session = sessionmaker(bind=engine)


def result_ok(data: dict) -> dict:
    """
    Функция возвращает ответ серверной части об успешно выполненной операции
    в стандартном унифицированном формате вместе с данными

    Args:
        data (dict): возвращаемые данные

    Returns:
        (dict): ответ об успешно выполненной операции
    """
    # Сбросить message_id (если функция вызывается в задаче анализа, признак resultObject)
    if data.get("resultObject", None) is not None and get_message_id() is not None:
        set_message_id(None)

    return {"data": data, "errorCode": 0, "ok": True}


def result_error(data: dict = None, error_code: int = -1, error: str = '') -> dict:
    """
    Функция возвращает ответ серверной части о НЕуспешно выполненной операции
    в стандартном унифицированном формате вместе с данными

    Args:
        data (dict): возвращаемые данные
        error_code (int, optional): код ошибки
        error (str, optional): текст ошибки

    Returns:
        (dict): ответ о НЕуспешно выполненной операции
    """
    if data is None:
        data = {}

    # Сбросить message_id
    if get_message_id() is not None:
        set_message_id(None)

    return {"data": data, "errorCode": error_code, "error": error, "ok": False}


def create_file(image: bytes, filename: str = None) -> dict:
    """
    Функция создаёт файл с заданным именем из набора байтов.
    Если имя не задано, оно будет сгенерировано с использованием uuid4.

    Args:
        image (bytes): набор байтов
        filename (str, optional): имя файла

    Returns:
        (dict): стандартный ответ с именем файла
    """
    if not filename:
        filename = 'img_' + str(uuid.uuid4()) + '.jpg'
    try:
        with open(filename, "wb") as f:
            f.write(image)
    except Exception as e:
        return result_error(error=str(e))
    return result_ok({"filename": filename})


def delete_file(filename: str) -> dict:
    """
    Функция удаляет файл с заданным именем.

    Args:
        filename (str): имя файла

    Returns:
        (dict): стандартный ответ
    """
    try:
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        return result_error(error=str(e))
    return result_ok({"filename": filename})


def get_filename(filename: str, root: str) -> dict:
    """
    Функция возвращает полный путь к файлу по краткому имени файла и имени каталога,
    в структуре которого выполняется поиск.
    Файл с заданным именем может найтись, может найтись многократно, может не найтись.

    Args:
        filename (str): имя файла
        root (str): имя каталога

    Returns:
        (dict): стандартный ответ
    """
    result = [
        os.path.join(dp, f)
        for dp, dn, filenames in os.walk(root)
        for f in filenames
        if f == os.path.basename(filename)  # совпадает по имени с заданным файлом
        and os.path.join(dp, f) != filename  # но не совпадает с ним по полному пути
    ]
    return result_ok({"filename_list": result})


def set_message_id(message_id: str | None):
    """
    Устанавливает message_id в текущем потоке (thread_local)

    Args:
        message_id (str | None): Id сообщения
    """
    thread_local.message_id = message_id


def get_message_id() -> str:
    """
    Возвращает значение message_id из текущего потока (thread_local)

    Returns:
        (str): значение message_id из thread_local
    """
    try:
        return thread_local.message_id
    except Exception as e:
        logger.warning(f'get_message_id: {e}')
        return ''


def save_result(file_content, json_result, message_id):
    print(json_result)
    try:
        # scrs_timestamp = json_result.get("image_file", {}).get("timestamp")
        scrs_timestamp = datetime.datetime.now().isoformat()
        scrs_path = json_result.get("image_file", {}).get("name")
        scrs_name = os.path.split(scrs_path)[-1]
        print(scrs_name)
        is_complete = json_result.get("isComplete")
        result_conf = json_result.get("confidence")
        _result_json = json.dumps(json_result)
        speed_ms = json_result.get("speedMs")
        materials = json.loads(json_result.get("materials"))
        username = json_result.get("username")

        with Session() as session:
            sql = text("select ifnull(max(id), 0) + 1 from cv_activity")
            print(sql)
            act_id = list(session.execute(sql))[0][0]

            # Формируем команду для создания activity
            sql = text("""
                insert into cv_activity (
                    id, 
                    class_id, 
                    scrs_timestamp,
                    scrs_path, 
                    is_complete, 
                    result_conf, 
                    result_json, 
                    speed_ms,
                    username
                )
                values (
                    :id,
                    0,
                    :scrs_timestamp,
                    :scrs_path, 
                    :is_complete, 
                    :result_conf, 
                    :result_json, 
                    :speed_ms,
                    :username
                )
            """)
            print(sql)
            sql_result = session.execute(
                sql,
                {
                    "id": act_id,
                    "scrs_timestamp": scrs_timestamp,
                    "scrs_path": scrs_name,
                    "is_complete": is_complete,
                    "result_conf": result_conf,
                    "result_json": _result_json,
                    "speed_ms": speed_ms,
                    "username": username
                }
            )
            print(sql_result)

            for m in materials:
                # Формируем команду для создания activity_mat
                sql = text("""
                    insert into cv_activity_mat (
                        id, 
                        act_id,
                        mat_class_id, 
                        coords,
                        conf
                    )
                    values (
                        (select ifnull(max(id), 0) + 1 from cv_activity_mat),
                        :act_id,
                        :mat_class_id, 
                        :coords,
                        :conf
                    )
                """)
                print(sql)
                sql_result = session.execute(
                    sql,
                    {
                        "act_id": act_id,
                        "mat_class_id": m.get("mlCode"),
                        "coords": str(m.get("coords")),
                        "conf": m.get("conf")
                    }
                )
                print(sql_result)

            session.commit()

        # сохраняем файл
        file_path = os.path.join(g_runs, scrs_name)
        file_creation_result = create_file(file_content, file_path)
        return {"ok": True, "file_name": file_creation_result}

    except Exception as e:
        logger.debug(f'Error: {e}')
        print(f'Error: {e}')
        return {"ok": False}


def create_user(json_result, message_id):
    print(json_result)
    try:
        user_name = json_result.get("username")
        user_email = json_result.get("useremail")
        user_password = json_result.get("userpassword")

        with Session() as session:
            ##########################################################
            # Проверка на дубликаты
            sql = text("select id from cv_user where name = :name")

            print(sql)
            sql_result = session.execute(
                sql,
                {
                    "name": user_name
                }
            )
            sql_result_list = list(sql_result)
            if len(sql_result_list) > 0:
                print(f'Error: Пользователь с таким именем уже существует')
                return result_error(error="Пользователь с таким именем уже существует", error_code=-501)

            sql = text("select id from cv_user where email = :email")

            print(sql)
            sql_result = session.execute(
                sql,
                {
                    "email": user_email
                }
            )
            sql_result_list = list(sql_result)
            if len(sql_result_list) > 0:
                print(f'Error: Пользователь с таким e-mail уже существует')
                return result_error(error="Пользователь с таким e-mail уже существует", error_code=-502)

            ##########################################################

            sql = text("select ifnull(max(id), 0) + 1 from cv_user")
            print(sql)
            user_id = list(session.execute(sql))[0][0]

            # Формируем команду для создания user
            sql = text("""
                insert into cv_user (
                    id, 
                    name,
                    email,
                    password
                )
                values (
                    :id,
                    :user_name,
                    :user_email,
                    :user_password
                )
            """)
            print(sql)
            sql_result = session.execute(
                sql,
                {
                    "id": user_id,
                    "user_name": user_name,
                    "user_email": user_email,
                    "user_password": user_password
                }
            )
            print(sql_result)

            session.commit()
        return result_ok(data={})

    except Exception as e:
        logger.debug(f'Error: {e}')
        print(f'Error: {e}')
        return result_error(error=str(e), error_code=-500)


def verify_user(json_result):
    print(json_result)
    try:
        user_data = json_result.get("userdata")
        user_password = json_result.get("userpassword")

        with Session() as session:
            ##########################################################
            sql = text("select id, name, email from cv_user where (name = :data or email = :data) and password = :password")

            print(sql)
            sql_result = session.execute(
                sql,
                {
                    "data": user_data,
                    "password": user_password
                }
            )
            sql_result_list = list(sql_result)
            if len(sql_result_list) == 0:
                print(f'Error: Пользователь не найден')
                return result_error(error="Пользователь не найден", error_code=-503)

            user_id = sql_result_list[0][0]
            user_name = sql_result_list[0][1]
            user_email = sql_result_list[0][2]
            print(user_id)
            data = {"user_id": user_id, "user_name": user_name, "user_email": user_email}

            ##########################################################

        return result_ok(data=data)

    except Exception as e:
        logger.debug(f'Error: {e}')
        print(f'Error: {e}')
        return result_error(error=str(e), error_code=-500)
