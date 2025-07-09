import os
import logging
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI

# -------------------------------------------------
# Basic setup
# -------------------------------------------------
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
if not os.environ.get("OPENAI_API_KEY"):
    logging.error("OPENAI_API_KEY not found in environment variables")

# -------------------------------------------------
# System prompt for SoulBridgeAI
# -------------------------------------------------
SYSTEM_PROMPT = """You are SoulBridgeAI, an emotionally intelligent assistant created to help
people process and understand their thoughts. Your tone is calm, supportive, and
deeply human — like a trusted friend who knows psychology, empathy, and how to speak
without judgment.

Guidelines:
1. Always acknowledge the user’s feelings.
2. Respond in a thoughtful, grounded (sometimes poetic) way.
3. Don’t rush to fix; guide gently with questions or reflections.
4. Offer comfort if they’re hurting; clarity if they’re confused.
5. Keep responses short when appropriate, or deeper when needed.
"""

# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.route("/")
def chat():
    # Start a fresh message list if it doesn’t exist
    if "messages" not in session:
        session["messages"] = []
    return render_template("chat.html")

@app.route("/send_message", methods=["POST"])
def send_message():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify(success=False, error="Message cannot be empty"), 400

        # Initialize messages if not exists
        if "messages" not in session:
            session["messages"] = []
        
        # Add user message to history
        session["messages"].append({"role": "user", "content": user_message})

        # Prepare messages for OpenAI
        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        api_messages.extend(session["messages"])

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=api_messages,
            max_tokens=500,
            temperature=0.7,
        )

        ai_message = response.choices[0].message.content.strip()
        session["messages"].append({"role": "assistant", "content": ai_message})

        # Trim history to the last 20 messages
        session["messages"] = session["messages"][-20:]

        return jsonify(success=True, response=ai_message)

    except Exception as e:
        logging.exception("Error in /send_message")
        error_message = str(e)
        
        # Provide more specific error messages
        if "insufficient_quota" in error_message:
            user_error = "⚠️ OpenAI API quota exceeded. Please check your billing settings at platform.openai.com"
        elif "rate_limit" in error_message or "429" in error_message:
            user_error = "⚠️ Too many requests. Please wait a moment and try again."
        elif "api_key" in error_message:
            user_error = "⚠️ API key issue. Please check your OpenAI API key configuration."
        else:
            user_error = "⚠️ I'm having trouble connecting right now. Please try again later."
        
        return jsonify(success=False, error=user_error), 500

# -------------------------------------------------
# API endpoint for Kodular integration
# -------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Simple API endpoint for Kodular integration
    Expected JSON: {"message": "user message"}
    Returns JSON: {"response": "ai response", "success": true/false}
    """
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify(success=False, error="Message field is required"), 400

        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify(success=False, error="Message cannot be empty"), 400

        # Simple API call without session storage for Kodular
        api_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=api_messages,
            max_tokens=500,
            temperature=0.7,
        )

        ai_message = response.choices[0].message.content.strip()
        return jsonify(success=True, response=ai_message)

    except Exception as e:
        logging.exception("Error in /api/chat")
        error_message = str(e)
        
        # Provide specific error messages
        if "insufficient_quota" in error_message:
            user_error = "OpenAI API quota exceeded. Please check billing settings."
        elif "rate_limit" in error_message or "429" in error_message:
            user_error = "Too many requests. Please wait and try again."
        elif "api_key" in error_message:
            user_error = "API key issue. Please check configuration."
        else:
            user_error = "Service temporarily unavailable. Please try again later."
        
        return jsonify(success=False, error=user_error), 500

# -------------------------------------------------
# CORS support for mobile apps
# -------------------------------------------------
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# -------------------------------------------------
# Run the server
# -------------------------------------------------
if __name__ == "__main__":
    app.run()