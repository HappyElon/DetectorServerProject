import argparse
from dependency_injector import providers

from src.app.containers import ApplicationContainer
from src.app.run_configurator import RunConfigurator

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=False, help='ws host')
    parser.add_argument('--port', required=False, help='ws port')
    args = parser.parse_args()

    # Создаём контейнер зависимостей
    container: ApplicationContainer = providers.Container(ApplicationContainer)
    runner = RunConfigurator(container)
    runner.run_using_uvicorn(args.host, args.port)
