import os
import logging
import sqlite3
from flask import Flask, request, jsonify, render_template
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

# Connect to SQLite database (or create it if it doesn't exist)
def get_db_connection():
    conn = sqlite3.connect('bot_messages.db')
    conn.row_factory = sqlite3.Row
    return conn

# Create a table to store messages if it doesn't exist
def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        message TEXT NOT NULL,
        is_bot BOOLEAN NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

create_table()

# Function to save a message to the database
def save_message(user_id, message, is_bot=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (user_id, message, is_bot) VALUES (?, ?, ?)', 
                  (user_id, message, is_bot))
    conn.commit()
    conn.close()

# Function to retrieve the last N messages from the database
def get_last_messages(user_id, n):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT message, is_bot 
        FROM messages 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (user_id, n))
    messages = cursor.fetchall()
    conn.close()
    return [f"{'Bot' if msg['is_bot'] else 'User'}: {msg['message']}" for msg in messages]

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
                        # Save user message to the database
                        save_message(sender_id, message_text, is_bot=False)

                        # Get conversation history
                        conversation_history = get_last_messages(sender_id, 15)
                        full_message = "Conversation so far:\n{}\n\nUser: {}".format(
                            '\n'.join(reversed(conversation_history)), message_text)

                        # Generate response
                        response = messageHandler.handle_text_message(full_message, message_text)
                        
                        # Save bot's response to the database
                        save_message(sender_id, response, is_bot=True)
                        
                        # Send the response
                        send_message(sender_id, response)
                    else:
                        default_response = "👍"
                        save_message(sender_id, default_response, is_bot=True)
                        send_message(sender_id, default_response)

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
        return jsonify({"error": "No query provided"}), 400
    
    # Pass the query to messageHandler and get the response
    response = messageHandler.handle_text_message(query, query)
    return jsonify(response)

@app.route('/api2', methods=['GET'])
def api2():
    user_query = request.args.get('query')  # Get the query parameter from the URL
    if not user_query:
        return jsonify({"error": "No query provided"}), 400
    
    # Pass the query to brain.py and get the response
    response_1, response_2 = query(user_query)
    return jsonify({"bing_response": response_1, "google_response": response_2})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
