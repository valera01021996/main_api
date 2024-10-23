import os
import paramiko
from minio_utils import upload_to_minio
from mm_utils import send_message_to_channel

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