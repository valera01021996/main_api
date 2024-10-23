import requests
import threading
from flask import Blueprint, request, jsonify
from utils.ssh_utils import process_alert
from utils.mm_utils import create_channel, add_user_to_channel, send_message_to_channel
from utils.redis_utils import save_alert_data

alert_bp = Blueprint('alert_bp', __name__)
user_ids = ['e5p8wt1qctds7kschqqjm197wy', '8bwmqn1djtnp3nw5ftmocpg7bh']

@alert_bp.route('/alert', methods=['POST'])
def alert_test():
    data = request.json
    print(data)

    status = data['alert_payload']['alerts'][0]['status']
    alertname = data['alert_payload']['alerts'][0]['labels']['alertname']
    host_name = data['alert_payload']['alerts'][0]['labels']['host']
    time = data['alert_group']['created_at']
    data_to_crm = {
        'alertname': alertname,
        'time': time,
        'status': status
    }

    message = (f"# 🔥 {status} 🔥\n"
               f"❗❗❗ {alertname} ❗❗❗\n"
               f"❗❗❗ Хост: {host_name} ❗❗❗\n"
               f"🕧 Время: {time}")

    alert_group_id = data['alert_group_id']

    channel_id = create_channel(alertname)

    buttons = [
        {
            "name": "Acknowledged",
            "integration": {
                "url": "http://10.10.0.147:5000/acknowledged",
                "context": {
                    "action": "acknowledged",
                    "channel_id": channel_id,
                    "host_name": host_name,
                    "alertname": alertname,
                    "alert_group_id": alert_group_id
                }
            },
            "type": "button",
            "style": "default"
        }

    ]

    add_user_to_channel(channel_id, user_ids)
    post_id = send_message_to_channel(channel_id, message, buttons)
    alert_data = {
        'alert_group_id': alert_group_id,
        'status': status,
        'alertname': alertname,
        'time': time,
        'channel_id': channel_id,
        'post_id': post_id
    }
    # Создание уникального ключа для Redis
    redis_key = f"alert:{host_name}:{alertname}:{alert_group_id}"

    # Сохранение данных в Redis
    save_alert_data(redis_key, alert_data)

    response_to_crm = requests.post("http://127.0.0.1:5004/create_issue", json=data_to_crm)
    print(response_to_crm.status_code)
    if response_to_crm.status_code == 200 or response_to_crm.status_code == 201:
        idreadable = response_to_crm.json()['idreadable']
        print(response_to_crm.json())
        print(response_to_crm.json()['status'])
        send_message_to_channel(channel_id,
                                f"### Создана заявка в YouTrack 📒{idreadable} [Ссылка](http://10.10.0.181:8080/issues?preview={idreadable})")
    threading.Thread(target=process_alert, args=(host_name, channel_id,)).start()

    return jsonify({"status": "success"}), 200
