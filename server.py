import os
import qrcode
import io
import base64
from flask import Flask, render_template, jsonify, send_from_directory, request
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from datetime import datetime
import logging

# set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = "party_secret_key"
socketio = SocketIO(app, cors_allowed_origins="*")

# Get IP from environment variable, fallback to localhost
SERVER_IP = os.getenv("SERVER_IP", "localhost")
SERVER_PORT = int(os.getenv("SERVER_PORT", "5000"))

# Party state and user tracking
party_state = {"status": "off"}
connected_users = {}


def generate_qr_code(url):
    """Generate QR code and return as base64 string"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Create QR code image
    qr_img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    buffer.seek(0)
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/png;base64,{qr_base64}"


@app.route("/admin")
def admin():
    """Admin panel - only accessible via admin.aliislamic.org"""
    return render_template("admin.html")


@app.route("/party")
def party():
    """Main party client page - accessible via party.aliislamic.org"""
    return send_from_directory("static", "client.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    """Serve static files - accessible via party.aliislamic.org/static/"""
    return send_from_directory("static", filename)


@app.route("/party_on")
def party_on():
    """Turn party mode ON - accessible from both domains"""
    party_state["status"] = "on"
    socketio.emit("party_mode", {"status": "on"})
    logger.info("🎉 Party Mode ACTIVATED")
    return jsonify({"message": "Party Mode Activated", "status": "on"})


@app.route("/party_off")
def party_off():
    """Turn party mode OFF - accessible from both domains"""
    party_state["status"] = "off"
    socketio.emit("party_mode", {"status": "off"})
    logger.info("😴 Party Mode DEACTIVATED")
    return jsonify({"message": "Party Mode Deactivated", "status": "off"})


@app.route("/party_status")
def party_status():
    """Get current party status - accessible from both domains"""
    return jsonify(party_state)


@app.route("/api/server_info")
def server_info():
    """Get server info with QR code - accessible from both domains"""
    # Always generate the party URL as the public party endpoint
    host = request.headers.get("Host", "party.aliislamic.org")
    
    # Force party subdomain for the public URL
    if host.startswith("admin."):
        party_host = host.replace("admin.", "party.")
    else:
        party_host = "party.aliislamic.org"
    
    # Determine protocol
    if request.headers.get("X-Forwarded-Proto") == "https":
        party_url = f"https://{party_host}"
    else:
        party_url = f"http://{party_host}"

    logger.info(f"Generated Party URL: {party_url}")

    qr_code = generate_qr_code(party_url)

    return jsonify(
        {
            "ip": SERVER_IP,
            "port": SERVER_PORT,
            "party_url": party_url,
            "qr_code": qr_code,
        }
    )


@app.route("/api/connected_users")
def get_connected_users():
    """Get list of connected users - accessible from both domains"""
    return jsonify(
        {"users": list(connected_users.values()), "count": len(connected_users)}
    )


@socketio.on("connect")
def handle_connect(auth=None):
    """Handle client connection"""
    # Get real client IP (accounting for proxy)
    client_ip = request.environ.get(
        "HTTP_X_FORWARDED_FOR", 
        request.environ.get("HTTP_X_REAL_IP", 
        request.environ.get("REMOTE_ADDR", "Unknown"))
    )
    
    # If there are multiple IPs in X-Forwarded-For, get the first one (original client)
    if "," in str(client_ip):
        client_ip = client_ip.split(",")[0].strip()
    
    user_agent = request.headers.get("User-Agent", "Unknown Device")

    # Store user info
    connected_users[request.sid] = {
        "id": request.sid,
        "ip": client_ip,
        "user_agent": user_agent,
        "connected_at": datetime.now().strftime("%H:%M:%S"),
        "device": get_device_type(user_agent),
    }

    logger.info(f"🎉 User connected: {client_ip} ({get_device_type(user_agent)}) - SID: {request.sid}")

    # Send current party state to newly connected client
    emit("party_mode", party_state)

    # Notify all clients of user connection
    socketio.emit(
        "user_connected",
        {"users": list(connected_users.values()), "count": len(connected_users)},
    )


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection"""
    if request.sid in connected_users:
        user_info = connected_users[request.sid]
        logger.info(f"👋 User disconnected: {user_info['ip']} ({user_info['device']}) - SID: {request.sid}")
        del connected_users[request.sid]

        # Notify all clients of user disconnection
        socketio.emit(
            "user_disconnected",
            {"users": list(connected_users.values()), "count": len(connected_users)},
        )


def get_device_type(user_agent):
    """Determine device type from user agent"""
    user_agent = user_agent.lower()
    if "mobile" in user_agent or "android" in user_agent:
        return "📱 Mobile"
    elif "tablet" in user_agent or "ipad" in user_agent:
        return "📟 Tablet"
    elif "mac" in user_agent:
        return "💻 Mac"
    elif "windows" in user_agent:
        return "🖥️ Windows"
    elif "linux" in user_agent:
        return "🐧 Linux"
    else:
        return "🌐 Unknown"


if __name__ == "__main__":
    logger.info("🎉 Party Server Starting...")
    logger.info(f"📱 Party client: https://party.aliislamic.org")
    logger.info(f"🔧 Admin panel: https://admin.aliislamic.org")
    logger.info(f"🌐 Server IP: {SERVER_IP}")
    logger.info(f"Server Port: {SERVER_PORT}")
    logger.info("=" * 50)
    socketio.run(app, host="0.0.0.0", port=SERVER_PORT, debug=True)