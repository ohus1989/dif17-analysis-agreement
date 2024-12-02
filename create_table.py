import json
from tqdm import tqdm

import requests
import psycopg2

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
def save_to_db(data, tab_data):
    error_temp=None
    try:
        # PostgreSQL 연결
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        select_query = """
            SELECT * FROM TB_KB_PRIMARY_INSURANCE_PRODUCT WHERE SALE_DATE=%(SALE_DATE)s AND TYPENAME= %(TYPENAME)s
        """

        # 데이터 삽입
        insert_query = """
        insert into tb_kb_primary_insurance_product (comp_code, comp_name, p_code, upfile, typename, per_type, cnt, sale_date, upfile1, upfile2, header, page, pcode_gbn, rnk, name, order1, seqno, rnum, type_code, type, totalcount, create_date, update_date) values (
            %(tabName)s, %(tabCd)s, %(P_CODE)s, %(UPFILE)s, %(TYPENAME)s, %(PER_TYPE)s, %(CNT)s, %(SALE_DATE)s, %(UPFILE1)s, %(UPFILE2)s, %(HEADER)s,
            %(PAGE)s, %(PCODE_GBN)s, %(RNK)s, %(NAME)s, %(ORDER1)s, %(SEQNO)s, %(RNUM)s, %(TYPE_CODE)s, %(TYPE)s, 
            %(TOTALCOUNT)s, 
            now(),now()
        );
        """
        print(f'tabName : {tab_data["tabName"]} , len : {len(data["list"])}')
        for item in tqdm(data["list"]):
            error_temp =item
            if not "P_CODE" in item:
                item["UPFILE"] = item.get("UPFILE", None)
                item["UPFILE1"] = item.get("UPFILE1", None)
                item["UPFILE2"] = item.get("UPFILE2", None)
                item["P_CODE"] = None
                item["tabName"] = tab_data.get("tabName", None)
                item["tabCd"] = tab_data.get("tabCd", None)
                cursor.execute(insert_query, item)
            else:
                cursor.execute(select_query, item)
                result_one = cursor.fetchone()
                if result_one:
                    print('exist data')
                else:
                    item["UPFILE"] = item.get("UPFILE", None)
                    item["UPFILE1"] = item.get("UPFILE1", None)
                    item["UPFILE2"] = item.get("UPFILE2", None)
                    item["P_CODE"] = item.get("P_CODE", None)
                    item["tabName"] = tab_data.get("tabName", None)
                    item["tabCd"] = tab_data.get("tabCd", None)
                    cursor.execute(insert_query, item)

        # 변경사항 저장
        conn.commit()

    except Exception as e:
        print(f"Error saving data to DB: {e}")
        print(f'error_temp: {error_temp}')
    finally:
        if conn:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    # 호출할 URL
    URL = "https://www.kblife.co.kr/customer-common/API/productList1.do"

    tab_type = [
        # {"tabType": "1", "tabName": "판매상품", "tabCd": "PRD"},
        # {"tabType": "2", "tabName": "KB라이프생명", "tabCd": "KBLF"},
        # {"tabType": "3", "tabName": "(구)KB생명", "tabCd": "KBOL"},
        # {"tabType": "4", "tabName": "(구)푸르덴셜생명", "tabCd": "PRUD"},
        {"tabType": "5", "tabName": "(구)한일생명", "tabCd": "HNIL"}
    ]
    try:
        for tab_data in tab_type:
            # 데이터 가져오기
            datas = {
                "paGroupCnt": 10,
                "pageIndex": "1",
                "pageSize": 9999,
                "pdNm": "",
                "srchType": "",
                "tabType": tab_data["tabType"]
            }
            json_data = fetch_data(URL, datas)
            print(json_data)
            # 데이터베이스에 저장
            save_to_db(json_data, tab_data)

        print("Data successfully saved to the database.")
    except Exception as error:
        print(f"An error occurred: {error}")
