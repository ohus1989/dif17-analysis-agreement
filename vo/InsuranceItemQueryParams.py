from pydantic import BaseModel, Field

class InsuranceItemQueryParams(BaseModel):
    name: str = Field(..., description="이름")  # 필수 값
    sale_date: str = Field(..., description="시작일")  # 선택 값
    p_code: str = Field(..., description="플랜코드")  # 선택 값