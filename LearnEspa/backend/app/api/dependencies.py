from fastapi import Request

from app.services.import_service import ImportService
from app.services.source_storage import SourceStorage
from app.workers.import_worker import ImportWorker


def get_import_service(request: Request) -> ImportService:
    return request.app.state.import_service


def get_source_storage(request: Request) -> SourceStorage:
    return request.app.state.source_storage


def get_worker(request: Request) -> ImportWorker:
    return request.app.state.worker


#它不定义网页接口，只负责从 app.state 取出服务：