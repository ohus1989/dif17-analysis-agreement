import streamlit as st
import psycopg2
import pandas as pd
import logging
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PostgreSQL 연결 정보
DB_CONFIG = {
    "dbname": "postgres",
    "user": "dif17",
    "password": "admin123",
    "host": "database-6.c1tev5en92ci.us-east-2.rds.amazonaws.com",
    "port": 54323,
}

# PostgreSQL에서 데이터 조회하는 함수
def fetch_data(name=None, sale_date=None, p_code=None):
    query = """
        SELECT *
            FROM TB_KB_PRIMARY_INSURANCE_PRODUCT
            WHERE (%(name)s ='' OR TYPENAME LIKE CONCAT('%%', %(name)s, '%%'))
              AND (%(sale_date)s IS NULL OR 
                   (
                       COALESCE(NULLIF(TRIM(split_part(sale_date, '~', 1)), ''), NULL)::date <= %(sale_date)s::date
                       AND %(sale_date)s::date <= COALESCE(NULLIF(TRIM(split_part(sale_date, '~', 2)), ''), '9999-12-31')::date
                   )
              )
              AND (%(p_code)s = '' OR p_code = %(p_code)s)
    """
    params={
        "name": name,
        "sale_date": sale_date,
        "p_code": p_code,
    }

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                # 쿼리 로그 출력
                logger.info("Executed query: %s", cur.query.decode('utf-8'))
                rows = cur.fetchall()
                colnames = [desc[0] for desc in cur.description]  # 컬럼 이름 가져오기
                return pd.DataFrame(rows, columns=colnames)
    except Exception as e:
        st.error(f"데이터베이스 오류: {e}")
        return pd.DataFrame()  # 빈 데이터프레임 반환

# 상태 관리: 선택된 행 저장
if "selected_row" not in st.session_state:
    st.session_state["selected_row"] = None
# Streamlit 화면 구성
st.title("데이터 조회 화면")

# 레이아웃 설정
col1, col2 = st.columns(2)

# 사이드바(우측 패널)
with st.sidebar:
    st.header("조회 조건")
    name = st.text_input("Name")
    sale_date = st.date_input("Sale Date")
    p_code = st.text_input("P_Code")
    search_button = st.button("조회")

# 데이터 조회 및 결과 표시
if search_button:
    results = fetch_data(name=name, sale_date=sale_date, p_code=p_code)

    if not results.empty:
        # 왼쪽 그리드: 데이터프레임
        with col1:
            st.subheader("왼쪽 그리드")

            # AgGrid 설정
            gb = GridOptionsBuilder.from_dataframe(results)
            gb.configure_selection('single')  # 단일 행 선택 가능
            grid_options = gb.build()

            # AgGrid 표시
            grid_response = AgGrid(
                results,
                gridOptions=grid_options,
                data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                update_mode='MODEL_CHANGED',
                theme='balham',  # 테마: 'blue', 'dark', 'light', 'material'
                height=400,
                fit_columns_on_grid_load=True
            )

            # 선택된 행
            selected_row = grid_response['selected_rows']
            if selected_row:
                st.session_state["selected_row"] = selected_row[0]  # 첫 번째 선택된 행 저장

        # 오른쪽 그리드: 선택된 행의 상세정보 표시
        with col2:
            st.subheader("오른쪽 그리드")
            if st.session_state["selected_row"] is not None:
                st.write("선택된 행의 세부정보:")
                st.json(st.session_state["selected_row"])  # 선택된 행을 JSON 형식으로 표시
            else:
                st.write("왼쪽에서 행을 선택하세요.")
    else:
        st.warning("조회 결과가 없습니다.")