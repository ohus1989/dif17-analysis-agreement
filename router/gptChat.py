import logging

from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

from openai import OpenAI, AsyncOpenAI
from pydantic import BaseModel, Field
from typing import List
from fastapi import APIRouter, Request
from config.dbConfig import DB_CONFIG

from redis_config.openai_file_redis import get_data, save_data

from fastapi.responses import StreamingResponse

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/analysis/gpt",
)

client = OpenAI()
async_client = AsyncOpenAI()


class UploadFile(BaseModel):
    seqno: str = Field(..., description="이름")  # 필수 값
    file_index: str = Field(..., description="시작일")  # 선택 값


def get_file_id(uploadFile: UploadFile):
    exist_data = get_data(uploadFile.seqno, uploadFile.file_index)
    if exist_data:
        return exist_data['id']
    else:
        select_param = {
            'seqno': uploadFile.seqno,
            'file_index': uploadFile.file_index
        }
        query = """
            SELECT * FROM TB_KB_PRIMARY_INSURANCE_PRODUCT_FILE WHERE SEQNO=%(seqno)s AND FILE_INDEX=%(file_index)s
        """
        try:
            import psycopg2
            with psycopg2.connect(**DB_CONFIG) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(query, select_param)
                    # 쿼리 로그 출력
                    logger.info("Executed query: %s", cur.query.decode('utf-8'))
                    row = cur.fetchone()
                    file = row['file_path']
        except Exception as e:
            return f"데이터베이스 오류: {e}"

        upload = client.files.create(
            file=open(file, "rb"),
            purpose='assistants'
        )
        simple_types = (str, int, float, bool)

        result_dict = {attr: getattr(upload, attr) for attr in dir(upload) if
                       not attr.startswith("_") and isinstance(getattr(upload, attr), simple_types)}
        save_data(uploadFile.seqno, uploadFile.file_index, result_data=result_dict)

        return result_dict['id']


@router.post("/file/upload/", )
def upload_file_openai(uploadFile: UploadFile):
    return get_file_id(uploadFile)


@router.post("/file/upload/list/", )
def upload_file_openai(uploadFileList: List[UploadFile]):
    result = []
    for uploadFile in uploadFileList:
        result.append(get_file_id(uploadFile))
    return result


async def stream_assistant_response(assistant_id, thread_id):
    stream = async_client.beta.threads.runs.stream(
        assistant_id=assistant_id,
        thread_id=thread_id
    )

    async with stream as stream:
        async for text in stream.text_deltas:
            yield f"data: {text}\n\n"


@router.post("/ask_query")
async def ask_query(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")

    assistant = client.beta.assistants.create(
        name="친근한 대화 전문가",
        instructions="당신은 대화하는데 친근감을 표현하는 전문가입니다. 너무 과하지 않는 선에서 내 대화에 성심 성의것 답변해주세요.",
        model="gpt-4o",
        # tools=[{"type": "file_search"}],
    )

    # 새로운 스레드 생성
    thread = client.beta.threads.create()
    # make sure thread exist
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=prompt
    )

    return StreamingResponse(stream_assistant_response(assistant.id, thread.id), media_type="text/event-stream")


@router.post("/ask_query/withOutAssistant")
async def ask_query(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")
    thread_id = body.get("thread_id")
    assistant_id = body.get("assistant_id")

    # make sure thread exist
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=prompt
    )

    return StreamingResponse(stream_assistant_response(assistant_id, thread_id), media_type="text/event-stream")


@router.post("/create/assistant")
def create_assistant(request: Request):
    assistant = client.beta.assistants.create(
        name="친근한 대화 전문가",
        instructions="당신은 대화하는데 친근감을 표현하는 전문가입니다. 너무 과하지 않는 선에서 내 대화에 성심 성의것 답변해주세요.",
        model="gpt-4o",
        # tools=[{"type": "file_search"}],
    )

    return assistant.id


@router.post("/create/thread")
def create_thread(request: Request):
    # 새로운 스레드 생성
    thread = client.beta.threads.create()

    return thread.id


@router.post("/create/file/assistant")
def create_assistant_file_search(request: Request):
    assistant = client.beta.assistants.create(
        name="협약서 전문 분석가",
        instructions="당신은 협약서 전문 분석가입니다. 지식 기반을 사용하여 질문에 답변하세요.",
        model="gpt-4o",
        tools=[{"type": "file_search"}],
    )

    return assistant.id


@router.post("/create/file/thread")
async def create_thread_file_search(request: Request):
    body = await request.json()
    files = body.get("files", "")

    thread = client.beta.threads.create()

    attachments = [{"file_id": file, "tools": [{"type": "file_search"}]} for file in files]

    thread_message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="assistant",
        content="파일 내용을 잘 기억해서, 다음에 나올 질문에 대해 성심성의것 답변해줘.",
        attachments=attachments,
    )
    # 새로운 스레드 생성

    return thread.id
