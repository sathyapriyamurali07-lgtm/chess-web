from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, emit
import chess
import uuid
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

games = {}
players = {}
move_history = {}
timers = {}

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
    players[room] = []
    move_history[room] = []
    timers[room] = {"white": 300, "black": 300}
    return {"room": room}

@socketio.on("join")
def on_join(data):
    room = data["room"]
    if room not in games:
        return

    join_room(room)

    if request.sid not in players[room]:
        players[room].append(request.sid)

    if len(players[room]) == 1:
        color = "white"
    elif len(players[room]) == 2:
        color = "black"
    else:
        color = "spectator"

    emit("color", color)

    emit("state", {
        "fen": games[room].fen(),
        "move": None,
        "turn": "white"
    })

    emit("timer_update", timers[room])

@socketio.on("move")
def on_move(data):
    room = data["room"]
    if room not in games:
        return

    board = games[room]
    move = chess.Move.from_uci(data["move"])

    if request.sid not in players[room]:
        return

    player_index = players[room].index(request.sid)
    player_color = "white" if player_index == 0 else "black"

    current_turn = "white" if board.turn == chess.WHITE else "black"

    if player_color != current_turn:
        return

    if move in board.legal_moves:
        san_move = board.san(move)
        board.push(move)

        move_history[room].append({
            "san": san_move,
            "fen": board.fen()
        })

        emit("state", {
            "fen": board.fen(),
            "move": san_move,
            "turn": "white" if board.turn == chess.WHITE else "black"
        }, room=room)

        if board.is_check():
            emit("check", room=room)

        if board.is_game_over():
            reason = "Checkmate" if board.is_checkmate() else \
                     "Stalemate" if board.is_stalemate() else "Draw"

            emit("game_over", {
                "result": board.result(),
                "reason": reason
            }, room=room)

@socketio.on("rematch")
def on_rematch(data):
    room = data["room"]
    if room not in games:
        return

    games[room] = chess.Board()
    move_history[room] = []
    timers[room] = {"white": 300, "black": 300}

    emit("state", {
        "fen": games[room].fen(),
        "move": None,
        "turn": "white"
    }, room=room)

    emit("timer_update", timers[room], room=room)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)