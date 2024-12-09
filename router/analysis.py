import logging
import os
from typing import Optional

import psycopg2
import psycopg2.extras
import requests
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from http import HTTPStatus
from pydantic import BaseModel, Field
from requests import get

from config.dbConfig import DB_CONFIG
from vo.InsuranceItemQueryParams import InsuranceItemQueryParams

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/analysis/gpt",
)


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.post("/insurance/")
async def get_primary_insurance_product(name: str = None, sale_date: str = None, p_code: str = None):
    insurance_product = {
        "name": name,
        "sale_date": sale_date,
        "p_code": p_code,
    }
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
            WHERE (%(name)s ='' OR %(name)s IS NULL OR A.TYPENAME LIKE CONCAT('%%', %(name)s, '%%'))
              AND (%(sale_date)s IS NULL OR 
                   (
                       COALESCE(NULLIF(TRIM(split_part(A.sale_date, '~', 1)), ''), NULL)::date <= %(sale_date)s::date
                       AND %(sale_date)s::date <= COALESCE(NULLIF(TRIM(split_part(A.sale_date, '~', 2)), ''), '9999-12-31')::date
                   )
              )
              AND (%(p_code)s = '' OR %(p_code)s IS NULL OR A.p_code = %(p_code)s)
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, insurance_product)
                # 쿼리 로그 출력
                logger.info("Executed query: %s", cur.query.decode('utf-8'))
                rows = cur.fetchall()
                return rows
    except Exception as e:
        return f"데이터베이스 오류: {e}"


@router.post("/insurance/item/")
async def get_primary_insurance_product(insuranceItemQueryParams: InsuranceItemQueryParams):
    insurance_product = {
        "name": insuranceItemQueryParams.name,
        "sale_date": insuranceItemQueryParams.sale_date,
        "p_code": insuranceItemQueryParams.p_code,
    }
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
                return row
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

    return file_path
