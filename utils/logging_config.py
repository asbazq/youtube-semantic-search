"""프로젝트 전체에서 공유하는 오류 파일 로깅 설정."""

import logging
import os
from pathlib import Path


def configure_error_file_logging() -> Path:
    """ERROR 이상 로그를 영구 보관 파일에 추가하고 경로를 반환한다."""
    log_path = Path(os.getenv("ERROR_LOG_FILE", "data/logs/error.log"))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path = log_path.resolve()

    root_logger = logging.getLogger()
    # 여러 모듈이 호출해도 같은 파일 핸들러를 중복해서 추가하지 않는다.
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            if Path(handler.baseFilename).resolve() == resolved_path:
                return log_path

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.ERROR)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | "
            "process=%(process)d | %(message)s"
        )
    )
    root_logger.addHandler(handler)
    return log_path

