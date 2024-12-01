import json

import requests
import psycopg2
from psycopg2 import sql

# PostgreSQL 데이터베이스 연결 정보
DB_CONFIG = {
    "dbname": "postgres",
    "user": "dif17",
    "password": "admin123",
    "host": "database-6.c1tev5en92ci.us-east-2.rds.amazonaws.com",
    "port": 54323,
}


# URL 호출 및 JSON 데이터 받아오기
def fetch_data(url, data):
    payload = json.dumps(data)
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, data=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch data. Status code: {response.status_code}")


# PostgreSQL에 데이터 삽입
def save_to_db(data):
    try:
        # PostgreSQL 연결
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 데이터 삽입
        insert_query = """
        insert into tb_kb_primary_insurance_product (comp_code, comp_name, p_code, upfile, typename, per_type, cnt, sale_date, upfile1, upfile2, header, page, pcode_gbn, rnk, name, order1, seqno, rnum, type_code, type, totalcount, create_date, update_date) values (
            '','', %(P_CODE)s, %(UPFILE)s, %(TYPENAME)s, %(PER_TYPE)s, %(CNT)s, %(SALE_DATE)s, %(UPFILE1)s, %(UPFILE2)s, %(HEADER)s,
            %(PAGE)s, %(PCODE_GBN)s, %(RNK)s, %(NAME)s, %(ORDER1)s, %(SEQNO)s, %(RNUM)s, %(TYPE_CODE)s, %(TYPE)s, 
            %(TOTALCOUNT)s, 
            now(),now()
        );
        """

        for item in data["list"]:
            item["UPFILE"] = item.get("UPFILE", None)
            cursor.execute(insert_query, item)

        # 변경사항 저장
        conn.commit()

    except Exception as e:
        print(f"Error saving data to DB: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    # 호출할 URL
    URL = "https://www.kblife.co.kr/customer-common/API/productList1.do"

    try:
        # 데이터 가져오기
        datas = {
            "paGroupCnt": 10,
            "pageIndex": "1",
            "pageSize": 20,
            "pdNm": "",
            "srchType": "",
            "tabType": "1"
        }
        json_data = fetch_data(URL, datas)
        print(json_data)
        # 데이터베이스에 저장
        save_to_db(json_data)

        print("Data successfully saved to the database.")
    except Exception as error:
        print(f"An error occurred: {error}")
