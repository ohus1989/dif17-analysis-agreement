import logging
import os
from http import HTTPStatus

import psycopg2
import psycopg2.extras
import requests
import base64
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from requests import get

from config.dbConfig import DB_CONFIG
from vo.CustomResponse import CustomResponse, ErrorCode

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v2/analysis/gpt",
)


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/insurance/")
async def get_primary_insurance_product(request: Request):
    insurance_product = dict(request.query_params)
    query = """
        SELECT A.*,
                   B_0.file_path AS summary_file_path,
                   B_1.file_path AS reference_file_path,
                   B_2.file_path AS dictionary_file_path
            FROM TB_KB_PRIMARY_INSURANCE_PRODUCT A
                     LEFT OUTER JOIN TB_KB_PRIMARY_INSURANCE_PRODUCT_FILE B_0
                                     ON A.seqno = B_0.seqno
                                         AND B_0.file_index = '0'
                                         AND A.upfile IS NOT NULL
                     LEFT OUTER JOIN TB_KB_PRIMARY_INSURANCE_PRODUCT_FILE B_1
                                     ON A.seqno = B_1.seqno
                                         AND B_1.file_index = '1'
                                         AND A.upfile1 IS NOT NULL
                     LEFT OUTER JOIN TB_KB_PRIMARY_INSURANCE_PRODUCT_FILE B_2
                                     ON A.seqno = B_2.seqno
                                         AND B_2.file_index = '2'
                                         AND A.upfile2 IS NOT NULL
            WHERE (COALESCE(NULLIF(%(name)s, ''), NULL) IS NULL OR A.TYPENAME LIKE CONCAT('%%', %(name)s, '%%'))
  AND (COALESCE(NULLIF(%(sale_date)s, ''), NULL) IS NULL OR 
       (
           -- 빈 문자열을 NULL로 처리한 후 날짜 비교
           COALESCE(NULLIF(TRIM(split_part(A.sale_date, '~', 1)), ''), '1900-01-01')::date <= COALESCE(NULLIF(%(sale_date)s, ''), '9999-12-31')::date
           AND COALESCE(NULLIF(%(sale_date)s, ''), '1900-01-01')::date <= COALESCE(NULLIF(TRIM(split_part(A.sale_date, '~', 2)), ''), '9999-12-31')::date
       )
  )
  AND (COALESCE(NULLIF(%(p_code)s, ''), NULL) IS NULL OR A.p_code = %(p_code)s)
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, insurance_product)
                # 쿼리 로그 출력
                logger.info("Executed query: %s", cur.query.decode('utf-8'))
                rows = cur.fetchall()
                response = (CustomResponse.builder() \
                            .set_data(rows) \
                            .set_code(ErrorCode.OK["code"]) \
                            .build())
                return response
    except Exception as e:
        return f"데이터베이스 오류: {e}"


@router.get("/insurance/item/")
async def get_primary_insurance_product(request: Request):
    insurance_product = dict(request.query_params)
    query = """
        SELECT A.*,
                   B_0.file_path AS summary_file_path,
                   B_1.file_path AS reference_file_path,
                   B_2.file_path AS dictionary_file_path
            FROM TB_KB_PRIMARY_INSURANCE_PRODUCT A
                     LEFT OUTER JOIN TB_KB_PRIMARY_INSURANCE_PRODUCT_FILE B_0
                                     ON A.seqno = B_0.seqno
                                         AND B_0.file_index = '0'
                                         AND A.upfile IS NOT NULL
                     LEFT OUTER JOIN TB_KB_PRIMARY_INSURANCE_PRODUCT_FILE B_1
                                     ON A.seqno = B_1.seqno
                                         AND B_1.file_index = '1'
                                         AND A.upfile1 IS NOT NULL
                     LEFT OUTER JOIN TB_KB_PRIMARY_INSURANCE_PRODUCT_FILE B_2
                                     ON A.seqno = B_2.seqno
                                         AND B_2.file_index = '2'
                                         AND A.upfile2 IS NOT NULL
            WHERE A.TYPENAME = %(name)s
            AND A.sale_date = %(sale_date)s
            AND A.p_code = %(p_code)s 
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, insurance_product)
                # 쿼리 로그 출력
                logger.info("Executed query: %s", cur.query.decode('utf-8'))
                row = cur.fetchone()
                response = (CustomResponse.builder() \
                            .set_data(row) \
                            .set_code(ErrorCode.OK["code"]) \
                            .build())
                return response
    except Exception as e:
        return f"데이터베이스 오류: {e}"


def download(url, file_name):
    with open(file_name, "wb") as file:  # open in binary mode
        response = get(url)  # get request
        file.write(response.content)  # write to file


class FileQueryParams(BaseModel):
    seqno: str = Field(..., description="The sequence number")  # 필수 값
    file_index: str = Field(None, description="Optional file index")  # 선택 값


def get_file_exist(params):
    query = """
        SELECT *
            FROM TB_KB_PRIMARY_INSURANCE_PRODUCT_FILE
            WHERE seqno = %(seqno)s
            AND   file_index = %(file_index)s
    """

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                # 쿼리 로그 출력
                logger.info("Executed query: %s", cur.query.decode('utf-8'))
                row = cur.fetchone()
                return row
    except Exception as e:
        return f"데이터베이스 오류: {e}"


def insert_file_info(params):
    query = """
        insert into TB_KB_PRIMARY_INSURANCE_PRODUCT_FILE(seqno, file_index, file_path, create_date)
            values (%(seqno)s,%(file_index)s,%(file_path)s,now())
    """

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                # 쿼리 로그 출력
                logger.info("Executed query: %s", cur.query.decode('utf-8'))
                return conn.commit()
    except Exception as e:
        return f"데이터베이스 오류: {e}"


@router.post("/file/")
async def get_primary_insurance_product_file(params: FileQueryParams):
    exist_data_info = {
        'seqno': params.seqno,
        'file_index': params.file_index,
    }
    exist_data = get_file_exist(exist_data_info)
    if exist_data and os.path.exists(exist_data['file_path']):
        return exist_data['file_path']

    if params.file_index =='2':
        url = f'https://www.kblife.co.kr/api/archive/archives/download/product-terms/{params.seqno}/{params.file_index}'
    else:
        url = f'https://www.kblife.co.kr/api/archive/archives/download/product-explain/{params.seqno}/{params.file_index}'
    # 파일 다운로드 요청

    # 다운로드 경로 설정
    save_dir = "./data/"
    os.makedirs(save_dir, exist_ok=True)  # 디렉토리가 없으면 생성

    response = requests.get(url, stream=True)

    # 응답 헤더에서 Content-Disposition 추출
    content_disposition = response.headers.get('content-disposition', '')
    # 파일 이름 추출
    filename = "default_filename.pdf"  # 기본 파일 이름 (헤더에 파일 이름 없을 때 대비)
    if 'filename=' in content_disposition:
        filename = content_disposition.split('filename=')[1].strip().split(';')[0]
        filename = filename.strip('"')  # 따옴표 제거
        # 문자열을 bytes로 변환
        broken_bytes = bytes(filename, 'latin1')
        # UTF-8로 디코딩
        filename = broken_bytes.decode('utf-8')

    if filename == 'default_filename.pdf':
        return JSONResponse({}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
    # 한글 파일 이름 디코딩 확인
    print(f"Decoded filename: {filename}")

    # 저장 경로 조합
    file_path = os.path.join(save_dir, filename)

    # 파일 저장
    with open(file_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)
    insert_info = {
        "seqno": params.seqno,
        "file_index": params.file_index,
        "file_path": file_path,
    }
    insert_file_info(insert_info)
    print(f"File downloaded to: {file_path}")

    response = (CustomResponse.builder() \
                .set_data(file_path) \
                .set_code(ErrorCode.OK["code"]) \
                .build())
    return response

@router.get("/file/download/{seqno}/{file_index}")
async def get_download_file(seqno: str, file_index: str):
    exist_data_info = {
        'seqno': seqno,
        'file_index': file_index,
    }
    exist_data = get_file_exist(exist_data_info)
    file_path = exist_data['file_path']

    if os.path.exists(file_path):
        # 파일 이름 추출
        filename = os.path.basename(file_path)

        # 파일 데이터를 Base64로 인코딩
        with open(file_path, "rb") as f:
            encoded_file = base64.b64encode(f.read()).decode("utf-8")

        # CustomResponse 사용
        response = (
            CustomResponse.builder()
            .set_data({"filename": filename, "file_content": encoded_file})
            .set_code(ErrorCode.OK["code"])  # ErrorCode.OK["code"]
            .set_message("File successfully retrieved")
            .build()
        )
        return response
    return {"error": "File not found"}

@router.get("/file/download/{seqno}/{file_index}/{file_name}")
async def get_download_file(seqno: str, file_index: str, file_name: str):
    exist_data_info = {
        'seqno': seqno,
        'file_index': file_index,
    }
    decoded_file_name = file_name.encode('latin1').decode('utf-8')
    exist_data = get_file_exist(exist_data_info)
    file_path = exist_data['file_path']

    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/octet-stream", filename=file_name, headers={"Content-Disposition": f"inline; filename={decoded_file_name}"})
    return {"error": "File not found"}