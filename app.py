from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit
import chess
import chess.engine
import uuid
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

games = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/game/<room>")
def game(room):
    return render_template("game.html", room=room)

@app.route("/create")
def create():
    room = str(uuid.uuid4())[:8]
    games[room] = chess.Board()
    return {"room": room}

@socketio.on("join")
def on_join(data):
    room = data["room"]
    join_room(room)
    emit("state", games[room].fen(), room=room)

@socketio.on("move")
def on_move(data):
    room = data["room"]
    move = chess.Move.from_uci(data["move"])
    board = games[room]

    if move in board.legal_moves:
        board.push(move)
        emit("state", board.fen(), room=room)

        if board.is_game_over():
            emit("game_over", board.result(), room=room)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)