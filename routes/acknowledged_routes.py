import requests
from config import TOKEN_ONCALL, NAUTOBOT_URL
from utils.mm_utils import send_message_to_channel, update_message
from flask import Blueprint, request, jsonify
from utils.redis_utils import get_alert_data
acknowledged_bp = Blueprint('acknowledged_bp', __name__)

headers_oncall = {
    "Authorization": f"{TOKEN_ONCALL}",
    "Content-Type": "application/json"
}


@acknowledged_bp.route('/acknowledged', methods=['POST'])
def acknowledged():
    data = request.json

    host_name = data.get("context", {}).get("host_name")
    channel_id = data.get("context", {}).get("channel_id")
    alertname = data.get("context", {}).get("alertname")
    alert_group_id = data.get("context", {}).get("alert_group_id")

    redis_key = f"alert:{host_name}:{alertname}:{alert_group_id}"
    status, time, post_id = get_alert_data(redis_key)

    payload = {'host_name': host_name}

    print(alert_group_id)
    if not alert_group_id:
        return jsonify({"status": "error", "message": "alert_group_id not found"}), 404
    oncall_api_url = f"http://10.10.0.238:8080/api/v1/alert_groups/{alert_group_id}/acknowledge"

    response = requests.post(oncall_api_url, headers=headers_oncall)
    data_to_wiki = {'title': 'test123123'}
    response_to_wiki = requests.post('http://localhost:5003/get_article_link', json=data_to_wiki)

    if response_to_wiki.status_code == 200:
        response_data = response_to_wiki.json()
        article_link = response_data.get('link')
        if article_link:
            send_message_to_channel(channel_id, "Дежурный ознакомился ❗❗❗\n"
                                                f"### [📖Статья, которая поможет Вам в решении данной проблемы]({article_link})")

    if response.status_code == 200:
        # Новое сообщение без кнопки
        new_message = (f"🚨 Alert acknowledged.\n\n"
                       f"{alertname}\n"
                       f"{status} - {host_name}\n"
                       f"{time}")

        update_message(channel_id, post_id, new_message)
        try:
            response = requests.post(NAUTOBOT_URL, json=payload)

            if response.status_code == 200:
                server_info = response.json()
                server_name = server_info['server_name']
                serial_number = server_info['serial_number']
                asset_tag = server_info['asset_tag']

                message_info_about_server = (
                    f"ℹИнформация о сервере: \n💻 **Hostname:** `{server_name}`\n"
                    f"🔑 **Serial Number:** `{serial_number}`\n"
                    f"🏷️ **Asset Tag:** `{asset_tag}`\n"
                )

                send_message_to_channel(channel_id, message_info_about_server)

        except:
            pass

        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "error"}), response.status_code
