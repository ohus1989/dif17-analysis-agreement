from datetime import datetime
from pydantic import BaseModel
from typing import Any, Optional

# Custom Response 모델 정의
class CustomResponse(BaseModel):
    timestamp: datetime
    message: Optional[str] = None
    real_message: Optional[str] = None
    data: Optional[Any] = None
    code: str

    @classmethod
    def builder(cls):
        # Builder를 생성하기 위한 클래스
        return cls.Builder()

    class Builder:
        def __init__(self):
            # 기본값 초기화
            self.timestamp = datetime.utcnow()
            self.message = None
            self.real_message = None
            self.data = None
            self.code = "OK"  # 기본 코드 설정

        def set_timestamp(self, timestamp: datetime):
            self.timestamp = timestamp
            return self

        def set_message(self, message: str):
            self.message = message
            return self

        def set_real_message(self, real_message: str):
            self.real_message = real_message
            return self

        def set_data(self, data: Any):
            self.data = data
            return self

        def set_code(self, code: str):
            self.code = code
            return self

        def set_error_code(self, code: "ErrorCode"):
            self.code = code.code
            self.message = code.message
            return self

        def build(self):
            return CustomResponse(
                timestamp=self.timestamp,
                message=self.message,
                real_message=self.real_message,
                data=self.data,
                code=self.code,
            )


# ErrorCode 정의 (Java의 ErrorCode와 유사)
class ErrorCode:
    OK = {"code": "200", "message": "Success","status": 200}
    RESOURCE_NOT_FOUND = {"code": "C002", "message": "Resource not found","status": 204}
    SERVER_ERROR = {"code": "E001", "message": "Internal server error","status": 500}

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

    @classmethod
    def get(cls, key: str):
        return cls(**cls.__dict__.get(key, cls.SERVER_ERROR))
