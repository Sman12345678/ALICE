import os
import logging
from flask import Flask, request, jsonify,render_template
from dotenv import load_dotenv
from flask_cors import CORS
import requests
import messageHandler  # Import the message handler module
import time
from collections import deque
from brain import query 
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
        user_memory[user_id] = deque(maxlen=2)
    user_memory[user_id].append(message)

# Function to retrieve conversation history for a user
def get_conversation_history(user_id):
    return "\n".join(user_memory.get(user_id, []))

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

                    if message_text:
                        # Update user memory
                        update_user_memory(sender_id, message_text)

                        # Get conversation history
                        conversation_history = get_conversation_history(sender_id)
                        full_message = f"Conversation so far:\n Focus Your response on the last message:\n{conversation_history}\n\nUser: {message_text}"
                        
                        # Generate response
                        response = messageHandler.handle_text_message(full_message)
                        send_message(sender_id, response)
                    else:
                        send_message(sender_id, "👍")

    return "EVENT_RECEIVED", 200

# Function to send messages (text only)
def send_message(recipient_id, message=None):
    params = {"access_token": PAGE_ACCESS_TOKEN}

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
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api', methods=['GET'])
def api():
    query = request.args.get('query')  # Get the query parameter from the URL
    if not query:
        return jsonify({"error": "No query provided"}), 400  # Return an error if no query is passed
    
    # Pass the query to messageHandler and get the response
    response = messageHandler.handle_text_message(query)
    
    return jsonify(response)  

@app.route('/api2', methods=['GET'])
def api2():
    user_query = request.args.get('query')  # Get the query parameter from the URL
    if not user_query:
        return jsonify({"error": "No query provided"}), 400  # Return an error if no query is passed
    
    # Pass the query to brain.py and get the response
    response_1, response_2 = query(user_query)
    
    return jsonify({"bing_response": response_1, "google_response": response_2})  # Return the responses as JSON

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=3000)
