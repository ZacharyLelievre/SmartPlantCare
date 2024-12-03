from flask import (
    Flask,
    render_template,
    jsonify,
    Response,
    request,
    redirect,
    url_for,
    session,
    flash
)
import paho.mqtt.client as mqtt
import json
import time
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Secret key for session management. Replace with a strong, random key in production.
app.secret_key = 'your_secret_key_here'  # <-- Replace this with a strong secret key!

# Define a single user with hashed password
USER = {
    "username": "admin",
    "password_hash": generate_password_hash("pwd")  # <-- Replace "password123" with your desired password
}

# MQTT Configuration
BROKER = "172.20.10.8"
PORT = 1883
TOPIC_SENSOR = "sensor/temperature"
TOPIC_LED = "control/led"    # Topic for controlling the LED
TOPIC_VALVE = "control/valve"  # Topic for controlling the Valve

# Data storage for sensor data
sensor_data = {"temperature": None, "humidity": None}

# Initialize MQTT Client
client = mqtt.Client()

# MQTT Handlers
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        # Subscribe to sensor data topics if needed
        client.subscribe(TOPIC_SENSOR)
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    data = msg.payload.decode()
    print(f"Received message on {msg.topic}: {data}")

    if msg.topic == TOPIC_SENSOR:
        # Expecting data in JSON format
        try:
            sensor_values = json.loads(data)
            temperature = sensor_values.get("temperature")
            humidity = sensor_values.get("humidity")
            sensor_data["temperature"] = temperature
            sensor_data["humidity"] = humidity
            print(f"Updated sensor data: Temp={temperature}C, Humidity={humidity}%")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
    # If you have other sensor topics, handle them here

client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(BROKER, PORT, 60)
except Exception as e:
    print(f"Couldn't connect to MQTT Broker: {e}")
    exit(1)

# Start MQTT loop in a separate thread
client.loop_start()

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Flask Routes

@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/historical')
@login_required
def historical():
    return render_template('historical.html')

@app.route('/live-data')
@login_required
def live_data():
    return render_template('livedata.html')

@app.route('/sensor-data')
@login_required
def sensor_data_stream():
    def generate():
        while True:
            json_data = json.dumps(sensor_data)
            yield f"data:{json_data}\n\n"
            time.sleep(2)  # Send data every 2 seconds
    return Response(generate(), mimetype='text/event-stream')

@app.route('/led-control', methods=['POST'])
@login_required
def led_control():
    # Get the LED state from the request
    data = request.get_json()
    state = data.get("state")
    if state not in ["ON", "OFF"]:
        return jsonify({"error": "Invalid state"}), 400

    # Publish the state to the MQTT topic
    client.publish(TOPIC_LED, state)
    return jsonify({"message": f"LED turned {state}"}), 200

@app.route('/valve-control', methods=['POST'])
@login_required
def valve_control():
    # Get the valve action from the request
    data = request.get_json()
    action = data.get("action")
    if action not in ["OPEN", "CLOSE"]:
        return jsonify({"error": "Invalid action"}), 400

    # Publish the action to the MQTT topic
    client.publish(TOPIC_VALVE, action)
    return jsonify({"message": f"Valve {action}ED"}), 200  # e.g., "Valve OPENED"

# Optional: Add a status route
@app.route('/status', methods=['GET'])
@login_required
def status():
    return jsonify({"status": "Flask server is running"}), 200

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == USER["username"] and check_password_hash(USER["password_hash"], password):
            session['logged_in'] = True
            session['username'] = username
            flash("You have successfully logged in.", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.", "danger")
            return render_template('login.html')
    return render_template('login.html')

# Logout Route
@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=5001, debug=True)
    finally:
        client.loop_stop()
        client.disconnect()