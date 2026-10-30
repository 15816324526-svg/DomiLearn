from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.textbook_imports import router as textbook_router
from app.api.vocabulary_study import router as vocabulary_router
from app.api.model_settings import router as model_settings_router
from app.api.imitation import router as imitation_router
from app.converters import DoclingConverter, FakeConverter, PdfConverter
from app.core.config import Settings, get_settings
from app.db.session import create_engine_from_settings, make_session_factory, upgrade_database
from app.services.import_service import ImportService, ServiceError
from app.services.fake_lesson_extraction import fake_first_lesson
from app.services.book_extraction import extract_book
from app.services.job_recovery import recover_interrupted_jobs
from app.services.pdf_validation import PdfValidationError
from app.services.source_storage import SourceStorage
from app.services.vocabulary_study import VocabularyStudyService
from app.services.model_settings import ModelSettingsStore
from app.services.deepseek_client import DeepSeekClient
from app.services.imitation import ImitationService
from app.workers.import_worker import ImportWorker

#定义一个叫 create_app 的函数。
# 它可以接收一份设置和一个 PDF 转换器；两者都可以不传。
# 函数最终返回一个 FastAPI 应用。
def create_app(settings: Settings | None = None, converter: PdfConverter | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.ensure_directories()
    engine = create_engine_from_settings(settings)
    upgrade_database(engine)
    factory = make_session_factory(engine)
    
    if converter is None:
        converter = FakeConverter() if settings.converter == "fake" else DoclingConverter()

    import_service = ImportService(factory, settings.storage_root)
    source_storage = SourceStorage(settings.storage_root, settings.max_pdf_bytes)
    worker = ImportWorker(
        factory,
        settings.storage_root,
        converter,
        settings.conversion_timeout_seconds,
        settings.worker_poll_seconds,
        lesson_extractor=fake_first_lesson if isinstance(converter, FakeConverter) else extract_book,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with factory.begin() as session:
            recover_interrupted_jobs(session)
        worker.start()
        yield
        worker.stop()

    #这行创建后端应用对象。之后接口、中间件和错误处理都注册到这个对象上。
    app = FastAPI(title="DomiLearn API", version="0.1.0", lifespan=lifespan)
    #添加 CORS 中间件
    #浏览器中的前端位于 127.0.0.1:5173，后端位于 127.0.0.1:8000。
    #端口不同，浏览器认为它们是不同来源。CORS 配置告诉后端：允许这些前端地址访问接口。
    #中间件可以理解为一层统一处理：每个请求进入具体接口前会经过它，每个响应返回浏览器前也会经过它。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["*"] ,
        allow_headers=["*"],
    )
    #保存共享服务
    #app.state 是 FastAPI 应用上的共享存放位置。
    #接口文件可以从 request.app.state 取出这些已经创建好的服务。
    app.state.settings = settings
    app.state.session_factory = factory
    app.state.import_service = import_service
    app.state.vocabulary_study_service = VocabularyStudyService(factory)
    model_client = DeepSeekClient(ModelSettingsStore(settings.storage_root))
    app.state.model_client = model_client
    app.state.imitation_service = ImitationService(factory, model_client)
    app.state.source_storage = source_storage
    app.state.worker = worker
    app.include_router(textbook_router)
    app.include_router(vocabulary_router)
    app.include_router(model_settings_router)
    app.include_router(imitation_router)

    #注册统一错误处理
    @app.exception_handler(ServiceError)
    async def handle_service_error(_request: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(PdfValidationError)
    async def handle_pdf_error(_request: Request, exc: PdfValidationError) -> JSONResponse:
        status = 413 if exc.code == "PDF_TOO_LARGE" else 400
        return JSONResponse(
            status_code=status,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    return app


app = create_app()
#python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
#python -m uvicorn	使用当前 Python 环境运行 Uvicorn
#app.main:app	    找到 app/main.py，再取出其中名叫 app 的变量
#--reload	        代码变化后自动重启，适合开发阶段
#--host 127.0.0.1	只监听本机访问
#--port 8000	    后端使用 8000 端口
