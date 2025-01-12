import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
import requests
import messageHandler  # Import the message handler module
import time
from collections import deque

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

# Store user message history
user_memory = {}

# Function to store the last three messages per user
def update_user_memory(user_id, message):
    if user_id not in user_memory:
        user_memory[user_id] = deque(maxlen=3)
    user_memory[user_id].append(message)

# Function to retrieve conversation history for a user
def get_conversation_history(user_id):
    return "\n".join(user_memory.get(user_id, []))

# Function to upload an image to Facebook's Graph API
def upload_image_to_graph(image_data):
    url = f"https://graph.facebook.com/v21.0/me/message_attachments"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    files = {"filedata": ("image.jpg", image_data, "image/jpeg")}
    data = {"message": '{"attachment":{"type":"image", "payload":{}}}'}

    try:
        response = requests.post(url, params=params, files=files, data=data)
        if response.status_code == 200:
            result = response.json()
            return {"success": True, "attachment_id": result.get("attachment_id")}
        else:
            logger.error("Failed to upload image: %s", response.json())
            return {"success": False, "error": response.json()}
    except Exception as e:
        logger.error("Error in upload_image_to_graph: %s", str(e))
        return {"success": False, "error": str(e)}

# Verification endpoint for Facebook webhook
@app.route('/webhook', methods=['GET'])
def verify():
    token_sent = request.args.get("hub.verify_token")
    if token_sent == VERIFY_TOKEN:
        logger.info("Webhook verification successful.")
        return request.args.get("hub.challenge", "")
    logger.error("Webhook verification failed: invalid verify token.")
    return "Verification failed", 403

# Main webhook endpoint to handle messages
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    logger.info("Received data: %s", data)

    if data.get("object") == "page":
        for entry in data["entry"]:
            for event in entry.get("messaging", []):
                if "message" in event:
                    sender_id = event["sender"]["id"]
                    message_text = event["message"].get("text")
                    message_attachments = event["message"].get("attachments")

                    if message_attachments:
                        try:
                            attachment = message_attachments[0]
                            if attachment["type"] == "image":
                                image_url = attachment["payload"]["url"]
                                image_response = requests.get(image_url)
                                image_response.raise_for_status()
                                image_data = image_response.content
                                response = messageHandler.handle_attachment(image_data, attachment_type="image")
                                send_message(sender_id, response)
                            elif attachment["type"] == "audio":
                                audio_url = attachment["payload"]["url"]
                                audio_response = requests.get(audio_url)
                                audio_response.raise_for_status()
                                audio_data = audio_response.content
                                response = messageHandler.handle_attachment(audio_data, attachment_type="audio")
                                send_message(sender_id, response)
                        except Exception as e:
                            logger.error("Error handling attachment: %s", str(e))
                            send_message(sender_id, "Error processing attachment.")
                    elif message_text:
                        # Update user memory
                        update_user_memory(sender_id, message_text)

                        # Get conversation history
                        conversation_history = get_conversation_history(sender_id)
                        full_message = f"Conversation so far:\n{conversation_history}\n\nUser: {message_text}"
                        
                        # Generate response
                        response = messageHandler.handle_text_message(full_message)
                        send_message(sender_id, response)
                    else:
                        send_message(sender_id, "Sorry, I didn't understand that message.")

    return "EVENT_RECEIVED", 200

# Function to send messages (text, image, or audio)
def send_message(recipient_id, message=None):
    params = {"access_token": PAGE_ACCESS_TOKEN}

    if isinstance(message, dict):
        message_type = message.get("type")
        content = message.get("content")

        if message_type == "image":
            data = {
                "recipient": {"id": recipient_id},
                "message": {
                    "attachment": {
                        "type": "image",
                        "payload": {"attachment_id": content}
                    }
                },
            }
        elif message_type == "audio":
            data = {
                "recipient": {"id": recipient_id},
                "message": {
                    "attachment": {
                        "type": "audio",
                        "payload": {"attachment_id": content}
                    }
                },
            }
    else:
        if not isinstance(message, str):
            message = str(message) if message else "An error occurred while processing your request."
        data = {
            "recipient": {"id": recipient_id},
            "message": {"text": message},
        }

    headers = {"Content-Type": "application/json"}
    response = requests.post(
        f"https://graph.facebook.com/v21.0/me/messages",
        params=params,
        headers=headers,
        json=data
    )

    if response.status_code == 200:
        logger.info("Message sent successfully to user %s", recipient_id)
    else:
        try:
            logger.error("Failed to send message: %s", response.json())
        except Exception:
            logger.error("Failed to send message. Status code: %d", response.status_code)

# Start the app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
