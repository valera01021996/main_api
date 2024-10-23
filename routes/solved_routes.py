from flask import Blueprint, request, jsonify
from utils.mm_utils import archive_channel

solved_bp = Blueprint('solved_bp', __name__)


@solved_bp.route('/solved', methods=['POST'])
def solved():
    channel_id = request.form.get('channel_id')
    print(channel_id)

    if not channel_id:
        return jsonify({"error": "channel_id is required"}), 400

    archive_channel(channel_id)

    return jsonify({"status": "success"}), 200
