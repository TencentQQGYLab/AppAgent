import sys
import os
import base64

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
from self_explorer_figma import init_exploration, run_exploration

app = Flask(__name__)
app.config["DEBUG"] = True
CORS(app, resources={r"/*": {"origins": "*"}})

exploration_thread = None
stop_event = threading.Event()
init_data = None

@app.route("/init", methods=["POST"])
def initialize():
    global init_data
    data = request.get_json()
    app_name = data["app"]
    app_name = app_name.replace(" ", "")
    url = data["url"]
    password = data.get("password", None)
    root_dir = data.get("root_dir", "./")

    init_data = init_exploration(app_name, url, password, root_dir)

    if "status" in init_data and init_data["status"] == "error":
        return jsonify({"status": "error", "message": init_data["message"]})

    return jsonify(
        {
            "status": "success",
            "message": "Initialization completed",
        }
    )

@app.route("/explore", methods=["POST"])
def explore():
    app.logger.info("Explore function called")
    global exploration_thread, stop_event, init_data

    if exploration_thread and exploration_thread.is_alive():
        return jsonify(
            {"status": "error", "message": "Exploration already in progress"}
        )

    if not init_data:
        return jsonify({"status": "error", "message": "Initialization not completed"})

    data = request.get_json()
    task_desc = data["task_desc"]
    persona_desc = data.get("persona_desc", "")

    stop_event.clear()
    exploration_thread = threading.Thread(
        target=run_exploration,
        args=(
            init_data,
            task_desc,
            persona_desc,
            stop_event,
            True,
        ),
    )
    exploration_thread.start()

    return jsonify({"status": "success", "message": "Exploration started"})

@app.route("/stop_exploration", methods=["POST"])
def stop_exploration():
    global exploration_thread, stop_event, init_data

    app.logger.info("Stop exploration function called")

    try:
        stop_event.set()

        if exploration_thread and exploration_thread.is_alive():
            exploration_thread.join(timeout=10)
            if exploration_thread.is_alive():
                raise TimeoutError("Exploration thread did not terminate in time")

        if init_data and "selenium_controller" in init_data:
            try:
                if hasattr(init_data["selenium_controller"], "driver"):
                    init_data["selenium_controller"].driver.quit()
            except Exception as e:
                app.logger.error(f"Error while closing Selenium browser: {str(e)}")

        init_data = None
        exploration_thread = None

        return jsonify(
            {
                "status": "success",
                "message": "Exploration stopped and resources cleaned up",
            }
        )

    except Exception as e:
        app.logger.error(f"Error in stop_exploration: {str(e)}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"An unexpected error occurred: {str(e)}",
                }
            ),
            500,
        )

@app.route("/exploration_status", methods=["GET"])
def exploration_status():
    global exploration_thread

    if exploration_thread and exploration_thread.is_alive():
        return jsonify({"status": "in_progress", "message": "Exploration is running"})
    else:
        return jsonify({"status": "idle", "message": "No exploration in progress"})

@app.route("/get_report", methods=["GET"])
def get_report():
    global init_data
    if not init_data or "report_log_path" not in init_data:
        return jsonify({"status": "error", "message": "Report not available"}), 404
    
    report_path = init_data["report_log_path"]
    if not os.path.exists(report_path):
        return jsonify({"status": "error", "message": "Report file not found"}), 404
    
    with open(report_path, "r") as f:
        report_content = f.read()
    
    return jsonify({"status": "success", "content": report_content})

@app.route('/get_image', methods=['POST'])
def get_image():
    file_path = request.json['file_path']
    full_path = os.path.join(init_data['task_dir'], file_path)

    if os.path.exists(full_path):
        with open(full_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return jsonify({"status": "success", "image_data": encoded_string})
    else:
        return jsonify({"status": "error", "message": f"File not found: {full_path}"}), 404


if __name__ == "__main__":
    app.run(debug=True)
