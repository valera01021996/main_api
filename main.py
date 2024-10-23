import os
import io
from datetime import timedelta
import paramiko
from minio import Minio
import requests
import json
import datetime
from flask import Flask, request, jsonify
import threading
import redis

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Настройки Mattermost
BASE_URL = 'https://chat.tsc.uz'
TOKEN = 'bay9pk87mjdmigwjxw4a7t83zr'
TEAM_ID = '5o75syrtzjboufgp3rdfxjjrao'
# USER_ID = 'e5p8wt1qctds7kschqqjm197wy'
user_ids = ['e5p8wt1qctds7kschqqjm197wy', '8bwmqn1djtnp3nw5ftmocpg7bh']
CERT_PATH = "Smallstep_Root_CA_40478178306672942733621103581865030166.crt"
TOKEN_NAUTOBOT = "a74c66e277146e7b4514c4f6cabe339e222547a0"
URL_NAUTOBOT = 'https://10.10.0.249/api/dcim/devices/'
TOKEN_ONCALL = "624263bc7e5d57a58b832d8600c00dd0b5fe905b4cd2cb96bf43e5a1f2ef5a26"
REDIS_HOST = "192.168.91.143"
headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

headers_nautobot = {
    "Authorization": f"Token {TOKEN_NAUTOBOT}",
    "Accept": "application/json"
}

headers_oncall = {
    "Authorization": f"{TOKEN_ONCALL}",
    "Content-Type": "application/json"
}

SOLVED_CATEGORY_ID = "123"

minio_client = Minio(
    "minio.tsc.uz:9000",
    access_key="VpPwYPTKfOf02U1yt0rh",
    secret_key="ff9ijTQupSOqrZQ6lVlZAu5G1HywtTufmJKMcusl",
    secure=False
)
bucket_name = "diags"

redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=1)


def create_channel(alertname):
    timestamp = datetime.datetime.now().strftime('%d-%b-%Y %H:%M:%S')
    # channel_name = f"{alert_name}-{timestamp.replace(' ', '-').replace(':', '-')}".lower()
    channel_name = f"{alertname.replace(' ', '-')}-{timestamp.replace(' ', '-').replace(':', '-')}".lower()
    print(channel_name)
    channel_data = {
        "team_id": TEAM_ID,
        "name": channel_name,
        "display_name": f"{alertname} - {timestamp}",
        "type": "O"  # "O" for public channel, "P" for private channel
    }

    create_channel_url = f'{BASE_URL}/api/v4/channels'
    response = requests.post(create_channel_url, headers=headers, json=channel_data, verify=CERT_PATH)

    if response.status_code == 201:
        channel = response.json()
        channel_id = channel['id']
        print('Канал успешно создан с ID:', channel_id)
        return channel_id
    else:
        print('Ошибка при создании канала:', response.status_code, response.text)
        exit(1)


def add_user_to_channel(channel_id, user_ids):
    add_user_url = f'{BASE_URL}/api/v4/channels/{channel_id}/members'
    for user_id in user_ids:
        add_user_data = {
            "user_id": user_id
        }
        response = requests.post(add_user_url, headers=headers, json=add_user_data, verify=CERT_PATH)

        if response.status_code == 201:
            print('Пользователь успешно добавлен в канал.')
        else:
            print('Ошибка при добавлении пользователя в канал:', response.status_code, response.text)
            exit(1)


def send_message_to_channel(channel_id, message, buttons=None):
    message_data = {
        "channel_id": channel_id,
        "message": message,
        "props": {}
    }
    if buttons:
        message_data["props"] = {
            "attachments": [{
                "text": "",
                "actions": buttons
            }]
        }

    print("Отправляемый JSON:", json.dumps(message_data, indent=2))
    response = requests.post(f'{BASE_URL}/api/v4/posts', headers=headers, json=message_data, verify=CERT_PATH)

    if response.status_code == 201:
        post_id = response.json()['id']
        print('Сообщение успешно отправлено в канал.')
        return post_id

    else:
        print('Ошибка при отправке сообщения в канал:', response.status_code, response.text)
        print("Ответ Mattermost:", response.text)
        exit(1)


def archive_channel(channel_id):
    archive_url = f'{BASE_URL}/api/v4/channels/{channel_id}'

    response = requests.delete(archive_url, headers=headers, verify=CERT_PATH)
    print(response.status_code)

    if response.status_code == 200 or response.status_code == 201:
        print(f"Канал {channel_id} успешно закрыт (архивирован).")
    else:
        print(f"Ошибка при закрытии (архивировании) канала: {response.status_code}, {response.text}")


def upload_to_minio(local_file_path, generated_file_name):
    with open(local_file_path, 'rb') as file_data:
        file_stat = os.stat(local_file_path)
        minio_client.put_object(bucket_name, generated_file_name, io.BytesIO(file_data.read()),
                                length=file_stat.st_size)
    url = minio_client.presigned_get_object(bucket_name, generated_file_name, expires=timedelta(hours=2))
    return url


def connect_via_ssh_to_host(hostname, port=22, username="root", password="123456"):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh_client.connect(hostname, port=port, username=username, password=password)
        stdin, stdout, stderr = ssh_client.exec_command('diagonal -g')
        stdout.channel.recv_exit_status()

        output_lines = stdout.readlines()
        generated_file_name = None
        for line in output_lines:
            if 'diag' in line:
                generated_file_name = line.strip().split(' ')[1].strip().split("/")[2]
                break
            else:
                print("Нет такого файла")

        remote_file_path = f"/ARCHIVE/{generated_file_name}"

        sftp_client = ssh_client.open_sftp()
        local_file_path = os.path.join('C:\\Users\\User\\PycharmProjects\\chatbot\\files', generated_file_name)
        sftp_client.get(remote_file_path, local_file_path)
        sftp_client.close()
        ssh_client.close()

        url = upload_to_minio(local_file_path, generated_file_name)
        print(url)
        return url

    except Exception as e:
        print(f"Произошла ошибка {e}")
        ssh_client.close()


def process_alert(hostname, channel_id):
    try:
        url = connect_via_ssh_to_host(hostname)
        # send_message_to_channel(channel_id, f"## [Скачать diagonal]({url})")
        send_message_to_channel(channel_id, f"### [Скачать diagonal]({url})")
    except Exception as e:
        print(f"Ошибка при обработке алерта: {e}")


@app.route('/alert', methods=['POST'])
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
    try:
        redis_client.set(redis_key, json.dumps(alert_data))
        redis_client.expire(redis_key, 86400)  # 24 часа
    except redis.RedisError as e:
        print(f"Ошибка при работе с Redis: {e}")

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


@app.route('/solved', methods=['POST'])
def solved():
    channel_id = request.form.get('channel_id')
    print(channel_id)

    if not channel_id:
        return jsonify({"error": "channel_id is required"}), 400

    archive_channel(channel_id)

    return jsonify({"status": "success"}), 200


@app.route('/acknowledged', methods=['POST'])
def acknowledged():
    data = request.json

    host_name = data.get("context", {}).get("host_name")
    channel_id = data.get("context", {}).get("channel_id")
    alertname = data.get("context", {}).get("alertname")
    alert_group_id = data.get("context", {}).get("alert_group_id")

    redis_key = f"alert:{host_name}:{alertname}:{alert_group_id}"
    try:
        alert_data_json = redis_client.get(redis_key)
        if not alert_data_json:
            return jsonify({"error": "Данные не найдены"}), 404
        alert_data = json.loads(alert_data_json)

        # Извлечение необходимых данных из alert_data
        status = alert_data.get('status')
        time = alert_data.get('time')
        post_id = alert_data.get('post_id')

    except redis.RedisError as e:
        print(f"Ошибка при работе с Redis: {e}")
        return jsonify({"error": "Ошибка сервера"}), 500

    # Ссылка для подключения в Nautobot
    app1_url = 'http://localhost:5001/get_server_info'
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
            response = requests.post(app1_url, json=payload)

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


def update_message(channel_id, post_id, new_message):
    update_data = {
        "id": post_id,
        "channel_id": channel_id,
        "message": new_message,
        "props": {}  # Удаляем props, чтобы убрать кнопки
    }

    response = requests.put(f'{BASE_URL}/api/v4/posts/{post_id}', headers=headers, json=update_data, verify=CERT_PATH)

    if response.status_code == 200:
        print('Сообщение успешно обновлено.')
    else:
        print('Ошибка при обновлении сообщения:', response.status_code, response.text)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
