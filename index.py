from flask import Flask, jsonify, request
import requests
import re

app = Flask(__name__)

MAILSLURP_API_KEYS = []
MAILSLURP_BASE_URL = 'https://api.mailslurp.com'
email_key_mapping = {}

@app.route('/update_api_keys', methods=['POST'])
def update_api_keys():
    global MAILSLURP_API_KEYS
    new_keys = request.json.get('api_keys')
    if not new_keys or not isinstance(new_keys, list):
        return jsonify({"error": "Invalid API keys format. Provide a list of keys."}), 400
    MAILSLURP_API_KEYS = new_keys
    return jsonify({"message": "API keys updated successfully."}), 200

@app.route('/add_api_keys', methods=['POST'])
def add_api_keys():
    global MAILSLURP_API_KEYS
    new_keys = request.json.get('api_keys')
    if not new_keys or not isinstance(new_keys, list):
        return jsonify({"error": "Invalid input. Provide a list of keys to add."}), 400
    added_keys = [key for key in new_keys if key not in MAILSLURP_API_KEYS]
    MAILSLURP_API_KEYS.extend(added_keys)
    return jsonify({"message": "API keys added successfully.", "added_keys": added_keys}), 200

@app.route('/delete_api_keys', methods=['POST'])
def delete_api_keys():
    global MAILSLURP_API_KEYS
    keys_to_delete = request.json.get('api_keys')
    if not keys_to_delete or not isinstance(keys_to_delete, list):
        return jsonify({"error": "Invalid input. Provide a list of keys to delete."}), 400

    deleted_keys = [key for key in keys_to_delete if key in MAILSLURP_API_KEYS]
    MAILSLURP_API_KEYS = [key for key in MAILSLURP_API_KEYS if key not in keys_to_delete]

    if deleted_keys:
        return jsonify({"message": "API keys deleted successfully.", "deleted_keys": deleted_keys}), 200
    return jsonify({"error": "No matching keys found to delete."}), 404

def get_email_with_multiple_keys():
    for api_key in MAILSLURP_API_KEYS:
        headers = {'x-api-key': api_key}
        response = requests.post(f'{MAILSLURP_BASE_URL}/inboxes', headers=headers)
        if response.status_code == 201:
            data = response.json()
            return data['id'], data['emailAddress'], api_key
    return None, None, None

@app.route('/getMailAddress', methods=['GET'])
def get_email():
    inbox_id, email_address, api_key_used = get_email_with_multiple_keys()
    if email_address:
        email_key_mapping[inbox_id] = api_key_used
        return jsonify({"TEMP_MAIL": f"{inbox_id}:{email_address}"}), 200
    else:
        return jsonify({"error": "Failed to generate email address using all keys"}), 500

@app.route('/get_otp', methods=['GET'])
def get_otp():
    inbox_id = request.args.get('mail_id')
    if not inbox_id:
        return jsonify({'error': 'mail_id parameter is missing'}), 400

    api_key = email_key_mapping.get(inbox_id)
    if not api_key:
        return jsonify({'error': 'Invalid or unknown mail_id'}), 400

    headers = {'x-api-key': api_key}
    response = requests.get(f'{MAILSLURP_BASE_URL}/inboxes/{inbox_id}/emails', headers=headers)
    if response.status_code == 200:
        emails = response.json()
        if emails:
            latest_email_id = emails[0]['id']
            email_response = requests.get(f'{MAILSLURP_BASE_URL}/emails/{latest_email_id}', headers=headers)
            if email_response.status_code == 200:
                email_data = email_response.json()
                message_body = email_data['body']
                otp = extract_otp_from_message(message_body)
                return jsonify({'OTP': otp}), 200
    return jsonify({'error': 'Failed to fetch OTP'}), 500

def extract_otp_from_message(message_body):
    """Extract OTP from the email content."""
    otp = re.findall(r'\b\d{6}\b', message_body)
    return otp[0] if otp else 'OTP not found'

# Vercel uses this as the entry point
app = app
