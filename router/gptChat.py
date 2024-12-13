import logging

from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

from typing_extensions import override
from openai import OpenAI, AsyncOpenAI, AsyncAssistantEventHandler
from pydantic import BaseModel, Field
from typing import List
from fastapi import APIRouter, Request
from config.dbConfig import DB_CONFIG

from redis_config.openai_file_redis import get_data, save_data

from fastapi.responses import StreamingResponse

from vo.CustomResponse import CustomResponse, ErrorCode
from langchain_core.prompts import PromptTemplate

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v2/analysis/gpt",
)

client = OpenAI(default_headers={"OpenAI-Beta": "assistants=v2"})
async_client = AsyncOpenAI(default_headers={"OpenAI-Beta": "assistants=v2"})


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

        return upload.id


@router.post("/file/upload/", )
def upload_file_openai(uploadFile: UploadFile):
    response = (CustomResponse.builder() \
                .set_data(get_file_id(uploadFile)) \
                .set_code(ErrorCode.OK["code"]) \
                .build())
    return response


@router.post("/file/upload/list/", )
def upload_file_openai(uploadFileList: List[UploadFile]):
    result = []
    for uploadFile in uploadFileList:
        result.append(get_file_id(uploadFile))
    response = (CustomResponse.builder() \
                .set_data(result) \
                .set_code(ErrorCode.OK["code"]) \
                .build())
    return response


class EventHandler(AsyncAssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    @override
    def on_message_done(self, message) -> None:
        # print a citation to the file searched
        message_content = message.content[0].text
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(
                annotation.text, f"[{index}]"
            )
            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = client.files.retrieve(file_citation.file_id)
                citations.append(f"[{index}] {cited_file.filename}")

        print(message_content.value)
        print("\n".join(citations))


async def stream_assistant_response(assistant_id, thread_id):
    stream = async_client.beta.threads.runs.stream(
        assistant_id=assistant_id,
        thread_id=thread_id,
    )

    async with stream as stream:
        async for delta in stream.text_deltas:
            yield f"data: {delta}\n\n"


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
    context = body.get("prompt", "")
    thread_id = body.get("thread_id")
    assistant_id = body.get("assistant_id")

    template = """### 목적
    이 어시스턴트는 업로드된 파일의 내용을 분석하여 사용자 질문에 정확히 답변하는 데 초점을 맞춥니다. 답변은 OpenAI 모델을 사용하여 생성되며, 참조된 항목의 문서 이름, 페이지 또는 섹션 번호, 그리고 해당 내용의 스니펫을 제공합니다.

    ### 대상 사용자
    대상은 파일 내용을 기반으로 질문에 대한 구체적이고 신뢰할 수 있는 답변을 필요로 하는 사용자입니다. 이 어시스턴트는 특히 계약서, 보고서, 또는 기술 문서를 검토하거나 이해하려는 사용자를 위한 것입니다.

    ### 답변 스타일
    - 답변은 전문적이고 신뢰할 수 있는 어조로 작성됩니다.
    - 답변에는 문서 이름, 위치(페이지 또는 섹션), 및 관련 콘텐츠 스니펫이 명확히 표시됩니다.

    ### 제한 사항
    - 어시스턴트는 문서 외부의 정보를 기반으로 추측하거나 의견을 제시하지 않습니다.
    - 문서와 관련 없는 질문에는 답변하지 않습니다.
    - 파일이 손상되었거나 읽을 수 없는 경우, 사용자에게 명확히 알려줍니다.

    ### 예시
    **질문:** "계약 종료 조건에 대해 알려주세요."
    **답변:** "계약 종료 조건은 다음과 같습니다: [...]"
    **File Name:** "contract_2023.pdf"
    **Page:** "12"
    **Snippet:** "계약 종료는 양 당사자의 서면 동의에 의해 가능합니다."

    **질문:** "보고서의 1분기 매출은 얼마인가요?"
    **답변:** "1분기 매출은 12% 증가했습니다."
    **File Name:** "financial_report_2024.pdf"
    **Page:** "5"
    **Snippet:** "2024년 1분기 매출은 12% 증가하며 $1.2M에 도달했습니다."

    ### 질문
    {context}
    """
    prompt = PromptTemplate.from_template(template)
    prompt = prompt.format(context=context)
    # prompt = context
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
    response = (CustomResponse.builder() \
                .set_data(assistant.id) \
                .set_code(ErrorCode.OK["code"]) \
                .build())
    return response


@router.post("/create/thread")
def create_thread(request: Request):
    # 새로운 스레드 생성
    thread = client.beta.threads.create()
    response = (CustomResponse.builder() \
                .set_data(thread.id) \
                .set_code(ErrorCode.OK["code"]) \
                .build())
    return response


@router.post("/create/file/assistant")
def create_assistant_file_search(request: Request):
    assistant = client.beta.assistants.create(
        name="협약서 전문 분석가",
        instructions="당신은 협약서 전문 분석가입니다. 지식 기반을 사용하여 질문에 답변하세요.",
        model="gpt-4o",
        tools=[{"type": "file_search"}],
    )
    response = (CustomResponse.builder() \
                .set_data(assistant.id) \
                .set_code(ErrorCode.OK["code"]) \
                .build())
    return response


@router.post("/create/file/thread")
async def create_thread_file_search(request: Request):
    body = await request.json()
    files = body.get("files", "")
    assistant_id = body.get("assistant_id")

    thread = client.beta.threads.create()

    attachments = [{"file_id": file, "tools": [{"type": "file_search"}]} for file in files]

    print(f'attachments : {attachments}')
    index = 0
    while True:
        index += 1
        if check_attachments(thread.id, assistant_id, attachments) or index == 5:
            break

    # 새로운 스레드 생성
    response = (CustomResponse.builder() \
                .set_data(thread.id) \
                .set_code(ErrorCode.OK["code"]) \
                .build())
    return response


# 업로드된 파일의 이름을 식별할 수 없습니다.
def check_attachments(thread_id, assistant_id, attachments):
    # Create a thread and attach the file to the message
    thread = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="assistant",
        content="""저는 해당 문서를 기반으로 답변 드리겠습니다.
    예제 : TRUE : ["prompt_advanced_methodology.pdf"]""",
        attachments=attachments,
    )
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content="""파일 내용을 잘 기억해서, 다음에 나올 질문에 대해 성심성의껏 답변해줘. 첨부된 파일 내용이 확인되면 파일 이름을 리스트 형태로 알려줘. I'm not making tool_resources. 혹시 첨부된 파일을 찾을 수 없다면 FALSE 라고 답변 해줘.
        예제 : TRUE : ["prompt_advanced_methodology.pdf"]
        """,
    )
    thread = client.beta.threads.retrieve(thread_id=thread_id)
    print(thread.tool_resources.file_search)

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )

    check = True
    # 찾을 문구
    phrase_false = """FALSE"""
    phrase_true = """TRUE"""
    # 응답 메시지 출력
    if run.status == 'completed':
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        for msg in messages:
            if phrase_false in msg.content[0].text.value:
                check = False
                return check
            elif phrase_true in msg.content[0].text.value:
                check = True
            print(f"[{msg.role.upper()}]/n{msg.content[0].text.value}/n")
    else:
        print(f"Run status: {run.status}")

    return check

@router.post("/create/file/all")
async def create_thread_file_search(uploadFileList: List[UploadFile]):
    file_list = []
    for file in uploadFileList:
        file_id = get_file_id(file)
        file_list.append(file_id)

    vector_store = client.beta.vector_stores.create(
        name="Product Documentation",
        file_ids=file_list
    )
    assistant = client.beta.assistants.create(
        name="협약서 전문 분석가",
        instructions="""You are a professional agreement analysis assistant and have access to files to answer questions about insurance documents.""",
        model="gpt-4o",
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
    )
    # 새로운 스레드 생성
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "assistant",
                "content": """### 목적
이 어시스턴트는 협약서를 전문적으로 분석하고, 사용자 질문에 정확히 답변하는 데 초점을 맞춥니다. 답변에는 지식 기반을 활용하며, 참조된 항목의 문서와 페이지 번호를 제공합니다.

### 대상 사용자
대상은 협약서를 검토하거나 이해하려는 사용자로, 법률 또는 계약 문서에 대한 전문적인 도움을 필요로 합니다.

### 답변 스타일
- 답변은 전문적이고 신뢰할 수 있는 어조로 작성됩니다.
- 답변에는 관련 문서와 페이지 번호를 명확히 표시해야 합니다.

### 제한 사항
- 어시스턴트는 문서 외의 정보를 기반으로 추측하거나 의견을 제시하지 않습니다.
- 문서와 관련 없는 질문에는 답변하지 않습니다.

### 예시
**질문:** "계약 종료 조건에 대해 알려주세요."
**답변:** "계약 종료 조건은 '협약서 2023' 문서의 12페이지에 명시되어 있습니다. 해당 조건은 다음과 같습니다: [...]"

**질문:** "이 계약서의 갱신 절차는 무엇인가요?"
**답변:** "갱신 절차는 '협약서 2023' 문서의 8페이지에 상세히 기술되어 있습니다. 주요 단계는 다음과 같습니다: [...]" """,
            }
        ],
    )
    response = (CustomResponse.builder() \
                .set_data({
        'thread_id': thread.id,
        'file_ids': file_list,
        'assistant_id': assistant.id,
    }) \
                .set_code(ErrorCode.OK["code"]) \
                .build())
    return response
