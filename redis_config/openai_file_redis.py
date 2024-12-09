from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()
import os

import redis

_REDIS_HOST = os.environ.get("REDIS_HOST")
_REDIS_PORT = os.environ.get("REDIS_PORT")
_REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")
# Redis에 연결
_redis_client = redis.StrictRedis(host=_REDIS_HOST, port=_REDIS_PORT, password=_REDIS_PASSWORD, db=0, decode_responses=True)

_prefix = 'openai-file'
_expire_time = 3600


# 데이터 저장 (search key와 result 데이터)
def save_data(seqno, file_index, result_data):
    # search key를 Redis 키로 변환
    redis_key = f"{_prefix}:{seqno}:{file_index}"
    # result 데이터를 Redis Hash로 저장
    _redis_client.hset(redis_key, mapping=result_data)
    _redis_client.expire(redis_key, _expire_time)  # 1시간 TTL
    print(f"Data saved for key: {redis_key}")


# 데이터 조회
def get_data(seqno, file_index):
    # search key를 Redis 키로 변환
    redis_key = f"{_prefix}:{seqno}:{file_index}"
    # Redis에서 Hash 데이터를 조회
    if _redis_client.exists(redis_key):
        result_data = _redis_client.hgetall(redis_key)
        print(f"Data retrieved for key: {redis_key}")
        return result_data
    else:
        print(f"No data found for key: {redis_key}")
        return None


# 데이터 삭제
def delete_data(seqno, file_index):
    # search key를 Redis 키로 변환
    redis_key = f"{_prefix}:{seqno}:{file_index}"
    if _redis_client.exists(redis_key):
        _redis_client.delete(redis_key)
        print(f"Data deleted for key: {redis_key}")
    else:
        print(f"No data to delete for key: {redis_key}")


if __name__ == '__main__':
    # 예제 데이터
    seqno = "501555927"
    file_index = "0"
    result_data = {
        "file_name": "20240401_상품요약서_KB 100세만족 달러연금보험 무배당.pdf",
        "file_id": "file-3C7xbiHdZjjWPWc17rLvr8",
        "bytes": "345590"
    }

    # 데이터 저장
    # save_data(seqno, file_index, result_data)

    # 데이터 조회
    retrieved_data = get_data(seqno, file_index)
    print("Retrieved Data:", retrieved_data)

    # 데이터 삭제
    # delete_data(seqno, file_index)
