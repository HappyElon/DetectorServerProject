import asyncio
import os
from typing import Any

from dependency_injector import providers, containers
from dependency_injector.containers import DeclarativeContainer
from dependency_injector.wiring import inject, Provide
from fastapi import FastAPI


# Главный контейнер зависимостей
class ApplicationContainer(DeclarativeContainer):
    # Устанавливаем пакеты, в которые нужно inject-ить зависимости
    wiring_config = containers.WiringConfiguration(packages=["src.routes",
                                                             "src.app"
                                                             ])

    # Основной конфиг приложения
    config = providers.Configuration()
    system_level = os.getenv('SYSTEMLEVEL', 'DEV')

    # Грузим конфиг --------
    if system_level.upper() in ('PROD', 'DEMO', 'TEST'):
        config.from_yaml("./resources/config/config_" + system_level.lower() + ".yaml")
    else:
        config.from_yaml("./resources/config/config.yaml")
    # ----------------------

    # Создаём бины ---------
    app = providers.Singleton(FastAPI)
    # ----------------------


def heavy_bean_init():
    container = providers.Container(ApplicationContainer)


# Функции для получения значения из конфига по его пути
@inject
async def async_prop(
        property_path: str,
        default: Any = None,
        config: dict = Provide[ApplicationContainer.config]
) -> str | dict:
    try:
        key_path = property_path.split(".")
        config_or_property: str | dict = config
        for key in key_path:
            config_or_property = config_or_property.get(key)
        if config_or_property is None:
            config_or_property = default
        return config_or_property
    except Exception as e:
        if default:
            return default
        else:
            raise e


def prop(property_path: str, default: Any = None):
    return asyncio.run(async_prop(property_path, default))
# ----------------------
