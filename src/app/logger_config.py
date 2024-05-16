import gzip
import shutil
import json
import logging
import os
from datetime import datetime
from logging import LogRecord
from logging.handlers import TimedRotatingFileHandler
from typing import BinaryIO, Iterable

from src.app.containers import prop
from src.app.utils import thread_local


class BaseArchivingTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Реализует архивирование логов через каждые `when` `interval`-ов
    `when`, `interval` - как у суперкласса
    `keep_files` - сколько файлов НЕ архивировать на каждой итерации
    `archive_suffix` - расширение архива: gz, zip...
    """

    def __init__(self, filename, when: str, interval: int, keep_files: int, archive_suffix: str) -> None:
        super().__init__(filename, when, interval, 0)
        self.archive_suffix = archive_suffix
        self.keep_files = keep_files

    def doRollover(self) -> None:
        super().doRollover()
        self.do_archiving(
            filter(
                lambda file_name: not str(file_name).endswith(self.archive_suffix),
                super().getFilesToDelete()[:-self.keep_files]
            )
        )

    def do_archiving(self, files_to_archive: Iterable[str]) -> None:
        for filename in files_to_archive:
            with open(filename, 'rb') as log:
                archive_filename = self.archive_file(log, filename)
                self.post_archiving(archive_filename)
            os.remove(filename)

    def post_archiving(self, archive_filename: str):
        pass

    def archive_file(self, file_content: BinaryIO, filename: str) -> str:
        raise AttributeError("У данного абстрактного класса не определён метод архивации")


class GzipArchivingTransferringTimedRotatingFileHandler(BaseArchivingTimedRotatingFileHandler):
    """
    Реализует архивирование логов в формате gzip
    """

    def __init__(self, filename, when: str, interval: int, keep_files: int, transfer_directory: str) -> None:
        super().__init__(filename, when, interval, keep_files, 'gz')
        self.transfer_directory = transfer_directory

    def archive_file(self, file_content: BinaryIO, filename: str) -> str:
        archive_filename = f'{filename}.{self.archive_suffix}'
        with gzip.open(archive_filename, 'wb') as comp_log:
            comp_log.writelines(file_content)
        return archive_filename

    def post_archiving(self, archive_filename: str):
        src = os.path.join(os.path.split(self.baseFilename)[0], archive_filename)
        dest = self.transfer_directory
        shutil.move(src, dest)


class LogSubstringFilter(logging.Filter):
    """
    Пропускает сообщение, если в поле `msg` есть подстрока substring
    """

    def __init__(self, substring=""):
        super().__init__()
        self._substring = substring

    def filter(self, record: LogRecord) -> bool:
        return record.getMessage().find(self._substring) == -1


class LogFileFormatter(logging.Formatter):
    def __init__(self):
        super().__init__()

    def formatMessage(self, record: logging.LogRecord) -> str:
        super().formatMessage(record)
        log_record = {
            'time': datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f'),
            'level': record.levelname,
            'module': record.module,
            'message': record.message,
        }

        # Добавляем message_id, если он установлен в текущем потоке
        message_id = getattr(thread_local, 'message_id', None)
        if message_id is not None:
            log_record['message_id'] = message_id

        # > INFO
        if record.levelno >= 30:
            log_record.update({
                'debug': {
                    'path': record.pathname,
                    'funcName': record.funcName,
                    'lineNumber': record.lineno,
                }
            })

        return json.dumps(log_record, ensure_ascii=False)


def get_log_filename() -> str:
    return "det-server"


def get_log_config() -> dict:
    # Читаем конфиг
    log_file_dir = prop('log.logDirectory', False)
    log_level: str = prop('log.level')
    log_rotation: dict = prop('log.rotation', False)

    # Сохраняем обработчики логов
    handlers: dict = {
        'console': {
            'formatter': 'console',
            'filters': ['metrics_endpoint_filter'],
            'class': 'logging.StreamHandler',
        },
    }
    if log_file_dir:
        if log_rotation:
            handlers.update({
                'file': {
                    'formatter': 'file',
                    'filters': ['metrics_endpoint_filter'],

                    '()': GzipArchivingTransferringTimedRotatingFileHandler,
                    'filename': f"{log_file_dir}/{get_log_filename()}.log",
                    # Архивирование логов через каждые `interval` `when`-ов
                    'when': log_rotation.get('when'),
                    'interval': log_rotation.get('interval'),
                    # После каждой итерации не более keepFiles старых логов останутся не заархивированными
                    'keep_files': log_rotation.get('keepFiles'),
                    'transfer_directory': log_rotation.get('archiving').get('transferDirectory')
                }
            })
        else:
            handlers.update({
                'file': {
                    'formatter': 'file',
                    'filters': ['metrics_endpoint_filter'],

                    'class': 'logging.FileHandler',
                    'filename': f"{log_file_dir}/{get_log_filename()}.log",
                    'encoding': 'utf8',
                }
            })

    log_config = {
        'version': 1,
        'filters': {
            'metrics_endpoint_filter': {
                '()': LogSubstringFilter,
                'substring': '/metrics'
            }
        },
        'formatters': {
            'console': {
                'format': '[%(asctime)s] [%(module)s] %(levelname)s : %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'file': {
                '()': lambda: LogFileFormatter(),
            },
        },
        'handlers': handlers,
        'root': {
            'handlers': list(handlers.keys()),
            'level': log_level,
            'propagate': False,
        },
        'loggers': {
            'uvicorn': {
                'handlers': list(handlers.keys()),
                'level': log_level,
                'propagate': False,
            },
            'app_logger': {
                'handlers': list(handlers.keys()),
                'level': log_level,
                'propagate': False,
            }
        },
    }
    return log_config
