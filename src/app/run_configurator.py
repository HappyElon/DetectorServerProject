import logging.config
from typing import Type

import uvicorn
from dependency_injector.containers import Container
from fastapi import APIRouter  # , Depends

# from src.app.security import authenticate_user_over_http
from src.app.containers import heavy_bean_init
from src.app.logger_config import get_log_config
from src.routes.det_operations import router as router_ws


class RunConfigurator:
    def __init__(self, container):
        self._container = container

        # Создаём конфиг логов
        self._log_config = get_log_config()
        logging.config.dictConfig(self._log_config)

        # Инициализируем тяжелые бины
        heavy_bean_init()

        # ----------------------
        # Получаем экземпляр приложения
        self._app = self._container.container.app()

        # Создаём базовый роутер на эндпоинт: /api
        # base_router = APIRouter(prefix="/api", dependencies=[Depends(authenticate_user_over_http)])
        base_router = APIRouter()

        # Подключаем внешние роутеры:
        base_router.include_router(router_ws)

        # Подключаем базовый роутер
        self._app.include_router(base_router)

    def overwrite_di_container(self, container: Container | Type[Container]):
        self._container.override(container)

    @property
    def app(self):
        return self._app

    def run_using_uvicorn(self, host, port):
        # Читаем параметры из конфига
        app_config: dict = self._container.config().get("app")
        _host = host
        if not host:
            _host = "0.0.0.0"
        _port: int = 8000
        if port:
            _port = int(port)
        else:
            _port = int(app_config.get("port"))
        ssl_certfile = app_config.get("sslCertfile")
        ssl_keyfile = app_config.get("sslKeyfile")

        # Запускаем сервер
        uvicorn.run(
            self._app,
            host=_host,
            port=_port,
            ws_max_size=100_000_000,
            ws_ping_interval=180.0,
            ws_ping_timeout=180.0,
            log_config=self._log_config,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile
        )
