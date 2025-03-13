from flask import Flask, render_template, url_for, redirect, session, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit
from forms import LoginForm, RegisterForm
from functools import wraps
from caravan import Game
from utils import loadCustomDeck, saveCustomDeck
import random
import sqlite3


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")
gamestate = None
active_games = [] # [gamestate, game_id]


@app.route("/")
def index():
    return render_template("index.html", gamestate=gamestate)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        connect = sqlite3.connect("caravan.db")
        db = connect.cursor()
        db.execute("""SELECT * FROM users WHERE username = ?;""", (username,))
        user = db.fetchone()
        print(user)
        if user is None:
            return redirect(url_for("login"))
        if check_password_hash(user[3], password):
            session["username"] = username
            return redirect(url_for("index"))

        return redirect(url_for("login"))

    else:
        return render_template("login.html", form=form)
    
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        hashed_password = generate_password_hash(password)


        connect = sqlite3.connect("caravan.db")
        db = connect.cursor()

        # check for duplicate username/email in db
        db.execute("""SELECT * FROM users WHERE username = ? OR email = ?;""", (username, email))
        is_duplicate_user = db.fetchone()
        if is_duplicate_user is not None:
            print("dupe detected")
            return render_template("register.html", form=form)

        db.execute("""INSERT INTO users (username, email, password)
                      VALUES (?, ?, ?);""", (username, email, hashed_password))
        connect.commit()

        return redirect(url_for("login"))

    else:
        return render_template("register.html", form=form)
    
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function
    
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))

@app.route("/decks")
@login_required
def decks():
    suits = ["♥", "♦", "♠", "♣"]
    faces = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    deck = []
    for suit in suits:
        for face in faces:
            deck.append(face+suit)
    return render_template("decks.html", deck=deck)

@login_required
@socketio.on("save_deck")
def save_deck(data):
    deck = data['selectedCards']
    print(deck)
    saveCustomDeck(session['username'], deck)

@socketio.on("create_game")
def create_game():
    global gamestate
    gamestate = Game()
    gamestate.startGame()   
    gamestate.game_started = True
    gamestate.is_singleplayer = True
    
    response_data = gamestate.to_dict()

    print("created game")
    emit("game_update", response_data, broadcast=True)

@login_required
@socketio.on("create_multiplayer_game")
def create_multiplayer_game():
    global gamestate
    gamestate = Game()
    gamestate.startGame()
    game_id = ''.join([str(random.randint(0, 9)) for i in range(5)])
    active_games.append([gamestate, game_id])

    gamestate.player1 = session["username"]
    print(f"setting {gamestate.player1} to player 1")
    gamestate.player2 = None
    gamestate.game_started = False
    gamestate.is_singleplayer = False
    gamestate.getValues()
    gamestate.game_id = game_id
    gamestate.waiting_for_player = True

    response_data = gamestate.to_dict()
    print("making a room #", game_id)
    emit("redirect", {"url": f"/game/{game_id}"})
    emit("game_update", response_data, broadcast=True)

@login_required
@socketio.on("join_multiplayer_game")
def join_multiplayer_game(data):
    for game in active_games:
        game_id = data['game_id']
        gamestate = game[0]
        if game[1] == game_id and gamestate.waiting_for_player == True:
            gamestate.waiting_for_player = False
            gamestate.getValues()
            gamestate.player2 = session["username"]
            print(f"setting {gamestate.player2} to player 2")

            gamestate.game_started = True

            response_data = gamestate.to_dict()

            emit("redirect", {"url": f"/game/{game_id}"})
            emit("game_update", response_data, broadcast=True)

@app.route("/game/<game_id>")
def game_page(game_id):
    # Check if the game exists
    for game in active_games:
        if game[1] == game_id:
            gamestate = game[0]
            return render_template("multiplayer.html", game_id=game_id, gamestate=gamestate)
            
    # Game not found, redirect to index
    return redirect(url_for("index"))


@socketio.on("create_game_ai")
@login_required
def create_game_ai():
    global gamestate
    gamestate = Game()
    gamestate.startGame()
    gamestate._is_vs_ai = True
    gamestate.game_started = True
    gamestate.is_singleplayer = True
    
    response_data = gamestate.to_dict()
 
    emit("game_update", response_data, broadcast=True)


@socketio.on("place_card")
def handle_place_card(data):
    hand_index = data["hand_index"]
    caravan_index = data["caravan_index"]
    if not gamestate:
        return

    print(gamestate)

    # Determine player based on hand index
    if gamestate.is_singleplayer == True:
        if hand_index < 8:
            player = "1"
        else:
            player = "2"
            hand_index -= 8  # Adjust index for player 2's hand

    # DETERMINE IF IT IS GAME VS AI, IF IT IS, PREVENT PLAYER 2 FROM MAKING A MOVE
    if gamestate._is_vs_ai == True:
        if player == "2":
            return
    
    # MULTIPLAYER GAMES
    if gamestate.game_id is not None:
        if gamestate.player1 == session["username"]:
            player = "1"
            print(f"setting player to 1")

            
        elif gamestate.player2 == session["username"]:
            print(f"setting player to 2")
            player = "2"
            hand_index -= 8

    # PLAYER 1 VARS
    if player == "1":
        direction1 = gamestate._caravans1_direction[caravan_index][0] if (gamestate._caravans1_direction[caravan_index] and isinstance(gamestate._caravans1_direction[caravan_index], list)) else None
        top_card_value1 = gamestate._board._caravans1[caravan_index][-1].value() if gamestate._board._caravans1[caravan_index] else None
        placed_card_value1 = gamestate._hand1.getHand()[hand_index].value()
        top_card_suit1 = gamestate._board._caravans1[caravan_index][-1].getSuit() if gamestate._board._caravans1[caravan_index] else None        
        placed_card_suit1 = gamestate._hand1.getHand()[hand_index].getSuit()
        print(f"direction1: {direction1}, top_card_value1: {top_card_value1}, placed_card_value1: {placed_card_value1}, top_card_suit1: {top_card_suit1}, placed_card_suit1: {placed_card_suit1}")
        placed_card_value2 = None
    # PLAYER 2 VARS
    if player == "2":
        direction2 = gamestate._caravans2_direction[caravan_index][0] if (gamestate._caravans2_direction[caravan_index] and isinstance(gamestate._caravans2_direction[caravan_index], list)) else None

        top_card_value2 = gamestate._board._caravans2[caravan_index][-1].value() if gamestate._board._caravans2[caravan_index] else None
        placed_card_value2 = gamestate._hand2.getHand()[hand_index].value() 
        top_card_suit2 = gamestate._board._caravans2[caravan_index][-1].getSuit() if gamestate._board._caravans2[caravan_index] else None
        placed_card_suit2 = gamestate._hand2.getHand()[hand_index].getSuit()
        print(f"direction2: {direction2}, top_card_value2: {top_card_value2}, placed_card_value2: {placed_card_value2}, top_card_suit2: {top_card_suit2}, placed_card_suit2: {placed_card_suit2}")
        placed_card_value1 = None
    gamestate.handleDirectionsSuits()


    if player == gamestate.getTurn() and gamestate.numturns > 5 and (placed_card_value1 != 11) and (placed_card_value1 != 13):
    
        # Make sure the index is valid
        if player == "1" and hand_index < len(gamestate._hand1.getHand()):
            valid_move = False
            # If no direction is set yet
            if direction1 is None:
                valid_move = True

            # PICTURE CARDS DONT NEED TO FOLLOW SUIT OR SEQUENCE
            if placed_card_value1 > 10:
                valid_move = True

            # CANNOT PLAY CARD OF SAME VALUE ATOP ITSELF (NOT COUNTING PICTURE CARDS)
            elif placed_card_value1 == top_card_value1:
                valid_move = False

            # If direction is set, check if card follows the direction or matches the suit
            elif direction1 == "ASC" and ((top_card_value1 < placed_card_value1) or (top_card_suit1 == placed_card_suit1)):
                valid_move = True
            elif direction1 == "DESC" and ((top_card_value1 > placed_card_value1) or (top_card_suit1 == placed_card_suit1)):
                valid_move = True
                
            if valid_move:
                print(f"valid move player: {player}")

                # FLIP FOR QUEEN
                if placed_card_value1 == 12:
                    # Get the queen's suit to update the caravan suit
                    queen_suit = gamestate._hand1.getHand()[hand_index].getSuit()
                    # Update the suit for the caravan
                    gamestate._caravans1_suit[caravan_index] = queen_suit
                    # Flip the direction
                    gamestate.flipOrder(caravan_index)

                gamestate.placeCard(player, hand_index, caravan_index)
                gamestate.flipTurn()
                gamestate._hand1.replenishHand()

        elif player == "2" and hand_index < len(gamestate._hand2.getHand()):
            valid_move = False
            
            # If no direction is set yet
            if not direction2:
                valid_move = True
            elif placed_card_value2 > 10:
                valid_move = True
            # CANNOT PLAY CARD OF SAME VALUE ATOP ITSELF (NOT COUNTING PICTURE CARDS)
            elif placed_card_value2 == top_card_value2:
                valid_move = False
            # If direction is set, check if card follows the direction or matches the suit
            elif direction2 == "ASC" and ((top_card_value2 < placed_card_value2) or (top_card_suit2 == placed_card_suit2)):
                valid_move = True
            elif direction2 == "DESC" and ((top_card_value2 > placed_card_value2) or (top_card_suit2 == placed_card_suit2)):
                valid_move = True
                
            if valid_move:
                print(f"valid move player: {player}")

                # FLIP FOR QUEEN
                if placed_card_value2 == 12:
                    # Get the queen's suit to update the caravan suit
                    queen_suit = gamestate._hand2.getHand()[hand_index].getSuit()
                    # Update the suit for the caravan
                    gamestate._caravans2_suit[caravan_index] = queen_suit
                    # Flip the direction
                    gamestate.flipOrder(caravan_index)

                gamestate.placeCard(player, hand_index, caravan_index)
                gamestate.flipTurn()
                gamestate._hand2.replenishHand()

    elif gamestate.numturns < 6 and player == gamestate.getTurn():
        # OPENING ROUND 3 TURNS EACH
        if player == "1" and hand_index < len(gamestate._hand1.getHand()) and placed_card_value1 < 11:
            if gamestate.opening_round_filled[caravan_index] == False:
                gamestate.opening_round_filled[caravan_index] = True
                gamestate.placeCard(player, hand_index, caravan_index)
                gamestate.flipTurn()
        elif player == "2" and hand_index < len(gamestate._hand2.getHand()) and placed_card_value2 < 11:
            if gamestate.opening_round_filled[caravan_index+3] == False:
                gamestate.opening_round_filled[caravan_index+3] = True
                gamestate.placeCard(player, hand_index, caravan_index)
                gamestate.flipTurn()

    else:
        print("It's Not your turn!")
    
    # Check for win after card placement
    game_winner = gamestate.checkForWin()
    if game_winner:
        if game_winner == "p1":
            gamestate.win_status = f"Player 1 Wins!"
        elif game_winner == "p2":
            gamestate.win_status = f"Player 2 Wins!"
    

    gamestate.getValues()

    # Include gamestate.win_status in the response
    response_data = gamestate.to_dict()
    response_data['player'] = player
    
    # Send updated game state to all clients
    print("Sending game_update:", response_data)

    emit("game_update", response_data, broadcast=True)

@socketio.on("discard_card")
def handle_discard_card(data):
    global gamestate
    if not gamestate:
        return        

    hand_index = data["hand_index"]

    # Determine player based on hand index
    if hand_index < 8:
        player = "1"
    else:
        player = "2"
        hand_index -= 8  # Adjust index for player 2's hand

    # DETERMINE IF IT IS GAME VS AI, IF IT IS, PREVENT PLAYER 2 FROM MAKING A MOVE
    if gamestate._is_vs_ai == True:
        if player == "2":
            return
        
    # MULTIPLAYER GAMES
    if gamestate.game_id is not None:
        if gamestate.player1 == session["username"]:
            player = "1"
            print(f"setting player to 1")

            
        elif gamestate.player2 == session["username"]:
            print(f"setting player to 2")
            player = "2"
            hand_index -= 8
        
    
    # Determine player based on who sent the request
    if player == gamestate.getTurn():
    
        # Make sure it's the player's turn and the hand index is valid
        if player == "1" and hand_index < len(gamestate._hand1.getHand()):
            gamestate.discardCard(player, hand_index)
            # gamestate.flipTurn()
            gamestate._hand1.replenishHand()
        elif player == "2" and hand_index < len(gamestate._hand2.getHand()):
            gamestate.discardCard(player, hand_index)
            # gamestate.flipTurn()
            gamestate._hand2.replenishHand()
    
    # Send updated game state to all clients
    emit("game_update", gamestate.to_dict(), broadcast=True)

@socketio.on("place_side_card")
def place_side_card(data):

    global gamestate
    if not gamestate:
        return
    if gamestate.numturns < 5:
        return


    hand_index = data["hand_index"]
    caravan_card_index = data["caravan_card_index"]
    caravan_index = data["caravan_index"]

    # Determine player based on hand index
    if gamestate.is_singleplayer == True:
        if hand_index < 8:
            player = "1"
        else:
            player = "2"
            hand_index -= 8  # Adjust index for player 2's hand

    # DETERMINE IF IT IS GAME VS AI, IF IT IS, PREVENT PLAYER 2 FROM MAKING A MOVE
    if gamestate._is_vs_ai == True:
        if player == "2":
            return
    
    # MULTIPLAYER GAMES
    if gamestate.game_id is not None:
        if gamestate.player1 == session["username"]:
            player = "1"
            print(f"setting player to 1")
    
        elif gamestate.player2 == session["username"]:
            print(f"setting player to 2")
            player = "2"
            hand_index -= 8

        else:
            return
        

    placed_card_value = gamestate._hand1.getHand()[hand_index].value() if player == "1" else gamestate._hand2.getHand()[hand_index].value()

    # Allow players to place K/J on either their own or opponent's caravans
    target_caravan_index = caravan_index if caravan_index < 3 else caravan_index - 3  # Convert to 0-2 range
    player_caravans = caravan_index < 3  # True if targeting player 1's caravans
    target_caravan = gamestate._board.getCaravan1()[target_caravan_index] if player_caravans else gamestate._board.getCaravan2()[target_caravan_index]
    if not target_caravan or caravan_card_index >= len(target_caravan):
        print("Invalid target caravan or card index")
        return

    if placed_card_value in [11, 13]:  # If it's a J or K
        # Use 0-5 range for caravans in bonus cards (0-2 for player 1, 3-5 for player 2)
        bonus_caravan_index = target_caravan_index if player_caravans else target_caravan_index + 3
        
        gamestate._bonus_cards.append([placed_card_value, bonus_caravan_index, caravan_card_index])  
        if player == "1":
            gamestate._hand1.removeCard(hand_index)
        else:
            gamestate._hand2.removeCard(hand_index)

        gamestate.flipTurn()
        if player == "1":
            gamestate._hand2.replenishHand()
        else:
            gamestate._hand1.replenishHand()
    else: 
        print("not a K or J, rejecting...")
            
    print("CARAVAN BONUSES", gamestate._bonus_cards)

    # SAME STUFF AS OTHER PLACE_CARD

    # Check for win after card placement
    game_winner = gamestate.checkForWin()
    if game_winner:
        if game_winner == "p1":
            gamestate.win_status = f"Player 1 Wins!"
        elif game_winner == "p2":
            gamestate.win_status = f"Player 2 Wins!"

    try:
        gamestate.getValues()

        # Include gamestate.win_status in the response
        response_data = gamestate.to_dict()
        response_data['player'] = player

        print(f"Caravan values 1: {gamestate.caravan_values1}")
        print(f"Caravan values 2: {gamestate.caravan_values2}")
        
        # Send updated game state to all clients
        print("Sending game_update:", response_data)
        emit("game_update", response_data, broadcast=True)
        
    except Exception as e:
        print(f"Error during side card placement: {e}")
        # If there's an error, provide feedback
        emit("game_update", {"error": "An error occurred during side card placement."}, broadcast=True)

@socketio.on("make_ai_move")
def make_ai_move():
    global gamestate
    if not gamestate:
        return

    if gamestate.getTurn() != "2":
        return
    
    timeout_counter = 0
    valid_move = False
    while (not valid_move) and timeout_counter < 50:
        timeout_counter += 1
        print(timeout_counter)
        caravan_index = random.randint(0, 2)
        hand_index = random.randint(0, min(4, len(gamestate._hand2.getHand())-1)) if gamestate._hand2.getHand() else 0
        # Only try to access caravan card index if the caravan has cards
        if len(gamestate._board.getCaravan2()[caravan_index]) > 0:
            caravan_card_index = random.randint(0, len(gamestate._board.getCaravan2()[caravan_index])-1)
        else:
            caravan_card_index = 0       
        player = "2"

        # make sure we have cards in the hand
        if not gamestate._hand2.getHand():
            break

        print(f"\n\ncaravan index: {caravan_index}, hand_index: {hand_index}, caravan card index {caravan_card_index}\n\n\ ")

        placed_card_value2 = gamestate._hand2.getHand()[hand_index].value() 
        top_card_value2 = gamestate._board._caravans2[caravan_index][-1].value() if gamestate._board._caravans2[caravan_index] else None
        direction2 = gamestate._caravans2_direction[caravan_index][0] if (gamestate._caravans2_direction[caravan_index] and isinstance(gamestate._caravans2_direction[caravan_index], list)) else None
        top_card_suit2 = gamestate._board._caravans2[caravan_index][-1].getSuit() if gamestate._board._caravans2[caravan_index] else None
        placed_card_suit2 = gamestate._hand2.getHand()[hand_index].getSuit()

        gamestate.handleDirectionsSuits()

        # HANDLE PLACING KINGS JACKS

        if gamestate.numturns > 5 and (placed_card_value2 == 11 or placed_card_value2 == 13):

            # Allow players to place K/J on either their own or opponent's caravans
            target_caravan_index = caravan_index * (random.randint(1, 2))
            # Only add bonus card if there's at least one card in the target caravan
            target_is_player1 = target_caravan_index < 3
            target_caravan = gamestate._board.getCaravan1()[target_caravan_index] if target_is_player1 else gamestate._board.getCaravan2()[target_caravan_index - 3]

            if target_caravan and len(target_caravan) > 0:
                valid_caravan_card_index = random.randint(0, len(target_caravan) - 1)
                gamestate._bonus_cards.append([placed_card_value2, target_caravan_index, valid_caravan_card_index])  
                gamestate._hand2.removeCard(hand_index)
                gamestate.flipTurn()
                gamestate._hand1.replenishHand()
                valid_move = True

        elif gamestate.numturns > 5 and (placed_card_value2 != 11) and (placed_card_value2 != 13):
            valid_move = False    
            # If no direction is set yet
            if not direction2:
                valid_move = True
            elif placed_card_value2 > 10:
                valid_move = True
            # CANNOT PLAY CARD OF SAME VALUE ATOP ITSELF (NOT COUNTING PICTURE CARDS)
            elif placed_card_value2 == top_card_value2:
                valid_move = False
            # If direction is set, check if card follows the direction or matches the suit
            elif direction2 == "ASC" and ((top_card_value2 < placed_card_value2) or (top_card_suit2 == placed_card_suit2)):
                valid_move = True
            elif direction2 == "DESC" and ((top_card_value2 > placed_card_value2) or (top_card_suit2 == placed_card_suit2)):
                valid_move = True
                    
            if valid_move:
                print(f"Valid move found: card: {placed_card_value2}, caravan {caravan_index}")
                    # FLIP FOR QUEEN
                if placed_card_value2 == 12:
                    # Get the queen's suit to update the caravan suit
                    queen_suit = gamestate._hand2.getHand()[hand_index].getSuit()
                    # Update the suit for the caravan
                    gamestate._caravans2_suit[caravan_index] = queen_suit
                # Flip the direction
                gamestate.flipOrder(caravan_index)
                gamestate.placeCard(player, hand_index, caravan_index)
                gamestate.flipTurn()
                gamestate._hand2.replenishHand()
            else:
                print(f"Invalid move: card: {placed_card_value2}, caravan {caravan_index}")


        elif gamestate.numturns < 6:
            # OPENING ROUND 3 TURNS EACH
            if hand_index < len(gamestate._hand2.getHand()) and placed_card_value2 < 11:
                if gamestate.opening_round_filled[caravan_index+3] == False:
                    gamestate.opening_round_filled[caravan_index+3] = True
                    gamestate.placeCard(player, hand_index, caravan_index)
                    gamestate.flipTurn()
                    valid_move = True

    
    # Check for win after card placement
    game_winner = gamestate.checkForWin()
    if game_winner:
        if game_winner == "p1":
            gamestate.win_status = f"Player 1 Wins!"
        elif game_winner == "p2":
            gamestate.win_status = f"Player 2 Wins!"

    try:
        gamestate.getValues()
        
        response_data = gamestate.to_dict()
        response_data['player'] = player

        print(f"Caravan values 1: {gamestate.caravan_values1}")
        print(f"Caravan values 2: {gamestate.caravan_values2}")
        
        # Send updated game state to all clients
        print("Sending game_update:", response_data)
        
        # Send updated game state to all clients
        emit("game_update", response_data, broadcast=True)
        
    except Exception as e:
        print(f"Error during AI move: {e}")
        # If there's an error, redirect to the index page or reset the game
        emit("game_update", {"error": "An error occurred. Starting a new game."}, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)