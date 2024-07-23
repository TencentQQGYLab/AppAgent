import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
from self_explorer_figma import init_exploration, run_exploration

app = Flask(__name__)
CORS(app)

exploration_thread = None
stop_event = threading.Event()
init_data = None

def send_webhook_notification(data):
    print(f"Webhook notification: {data}")

@app.route("/init", methods=["POST"])
def initialize():
    global init_data
    data = request.get_json()
    app_name = data["app"]
    url = data["url"]
    password = data.get("password", None)
    root_dir = data.get("root_dir", "./")

    init_data = init_exploration(app_name, url, password, root_dir)
    if "status" in init_data and init_data["status"] == "error":
        return jsonify({"status": "error", "message": init_data["message"]})
    
    return jsonify({"status": "success", "message": "Initialization completed"})

@app.route("/explore", methods=["POST"])
def explore():
    global exploration_thread, stop_event, init_data

    if exploration_thread and exploration_thread.is_alive():
        return jsonify({"status": "error", "message": "Exploration already in progress"})

    if not init_data:
        return jsonify({"status": "error", "message": "Initialization not completed"})

    data = request.get_json()
    task_desc = data["task_desc"]
    persona_desc = data.get("persona_desc", "")

    stop_event.clear()
    exploration_thread = threading.Thread(
        target=run_exploration,
        args=(init_data, task_desc, persona_desc, send_webhook_notification, stop_event)
    )
    exploration_thread.start()

    return jsonify({"status": "success", "message": "Exploration started"})

@app.route("/stop_exploration", methods=["POST"])
def stop_exploration():
    global exploration_thread, stop_event, init_data

    if exploration_thread and exploration_thread.is_alive():
        stop_event.set()
        exploration_thread.join()

        # Selenium 브라우저 종료
        if init_data and 'selenium_controller' in init_data:
            init_data['selenium_controller'].close()

        return jsonify({"status": "success", "message": "Exploration stopped and browser closed"})
    else:
        return jsonify({"status": "error", "message": "No exploration in progress"})

@app.route("/exploration_status", methods=["GET"])
def exploration_status():
    global exploration_thread

    if exploration_thread and exploration_thread.is_alive():
        return jsonify({"status": "in_progress", "message": "Exploration is running"})
    else:
        return jsonify({"status": "idle", "message": "No exploration in progress"})

if __name__ == "__main__":
    app.run(debug=True)
