from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_socketio import SocketIO, emit
import uuid
import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

login_requests = {}
EXPIRE_SECONDS = 180
connected_clients = {}  # request_id: sid

def is_expired(timestamp):
    return (datetime.datetime.utcnow() - timestamp).total_seconds() > EXPIRE_SECONDS

request_page_html = """
<h2>로그인 요청</h2>
<p>요청자: {{ username }}</p>
<p>request_id: {{ request_id }}</p>
<form method="post" action="/approve">
    <input type="hidden" name="request_id" value="{{ request_id }}">
    <button type="submit">승인</button>
</form>
<form method="post" action="/reject">
    <input type="hidden" name="request_id" value="{{ request_id }}">
    <button type="submit">거부</button>
</form>
"""

@app.route('/')
def home():
    return "서버 정상 작동 중입니다. /request.html에서 로그인 요청을 생성해보세요."

@app.route('/login/request', methods=['POST'])
def login_request():
    username = request.json.get("username")
    if not username:
        return jsonify({"error": "Missing username"}), 400

    request_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow()

    login_requests[request_id] = {
        "username": username,
        "status": "pending",
        "timestamp": timestamp
    }

    return jsonify({
        "request_id": request_id,
        "status": "pending",
        "link": f"/request/{request_id}"
    })

@app.route('/request/<request_id>', methods=['GET'])
def view_request(request_id):
    data = login_requests.get(request_id)
    if not data:
        return "존재하지 않는 요청입니다.", 404
    return render_template_string(request_page_html,
                                  username=data['username'],
                                  request_id=request_id)

@app.route('/approve', methods=['POST'])
def approve():
    request_id = request.form.get("request_id")
    if request_id in login_requests:
        if is_expired(login_requests[request_id]['timestamp']):
            login_requests[request_id]['status'] = 'expired'
        else:
            login_requests[request_id]['status'] = 'approved'
            if request_id in connected_clients:
                sid = connected_clients[request_id]
                socketio.emit("status_update", {"status": "approved"}, to=sid)
    return "승인 완료!"

@app.route('/reject', methods=['POST'])
def reject():
    request_id = request.form.get("request_id")
    if request_id in login_requests:
        login_requests[request_id]['status'] = 'rejected'
        if request_id in connected_clients:
            sid = connected_clients[request_id]
            socketio.emit("status_update", {"status": "rejected"}, to=sid)
    return "거부 처리 완료."

@app.route('/request.html')
def serve_request_page():
    return send_from_directory('.', 'request.html')

@socketio.on("connect_wait")
def connect_wait(data):
    request_id = data.get("request_id")
    connected_clients[request_id] = request.sid
    emit("status_update", {"status": "connected"})

if __name__ == '__main__':
    socketio.run(app, debug=True)

#웹소켓 설정 python3 -m venv venv 가상환경생성(현재 가상환경 파일이 만들어짐 venv파일)
# source ven/bin/activate 활성화
# pip install flask-socketio 반드시 가상환경을 활성화 하여야 합니다.

