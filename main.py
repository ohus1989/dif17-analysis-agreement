from fastapi import FastAPI, Request, status
from router import analysis, gptChat
from fastapi.exceptions import RequestValidationError
from fastapi.logger import logger
from fastapi.responses import JSONResponse
import json

app = FastAPI()
app.include_router(analysis.router)
app.include_router(gptChat.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_body = await request.body()

    try:
        # JSON 데이터일 경우 디코딩
        json_body = json.loads(request_body)
    except json.JSONDecodeError:
        json_body = request_body.decode('utf-8')

        # 요청의 세부 내용을 출력
    print(f"Request URL: {request.url}")
    print(f"Request method: {request.method}")
    print(f"Request headers: {request.headers}")
    print(f"Request body: {json_body}")

    logger.error(
        "Request validation failed:\n" + str(exc) + "\nRequest:\n" + str(request_body.decode())
    )

    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
    # or logger.error(f'{exc}')
    logger.error(request, exc_str)
    content = {'status_code': 10422, 'message': exc_str, 'data': None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
