import datetime
import requests
import json
from config import TEAM_ID, BASE_URL, TOKEN, CERT_PATH

headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}


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
