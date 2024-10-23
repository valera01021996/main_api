import redis
import json
from config import REDIS_HOST
from flask import jsonify

redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=1)


def save_alert_data(redis_key, alert_data):
    try:
        redis_client.set(redis_key, json.dumps(alert_data))
        redis_client.expire(redis_key, 86400)  # 24 часа
    except redis.RedisError as e:
        print(f"Ошибка при работе с Redis: {e}")


def get_alert_data(redis_key):
    try:
        alert_data_json = redis_client.get(redis_key)
        if not alert_data_json:
            return jsonify({"error": "Данные не найдены"}), 404
        alert_data = json.loads(alert_data_json)

        # Извлечение необходимых данных из alert_data
        status = alert_data.get('status')
        time = alert_data.get('time')
        post_id = alert_data.get('post_id')
        return status, time, post_id

    except redis.RedisError as e:
        print(f"Ошибка при работе с Redis: {e}")
        return jsonify({"error": "Ошибка сервера"}), 500
