from flask import Flask, render_template, url_for, redirect, session, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room
from forms import LoginForm, RegisterForm
from functools import wraps
from caravan import Game
from utils import loadCustomDeck, saveCustomDeck
import random
import sqlite3
import json
import time


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")
gamestate = None
active_games = [] # [gamestate, game_id, gametype]

# @app.errorhandler(Exception)
# def handle_exception(e):
#     print(f"Unhandled Exception: {e}")  
#     return render_template("index.html", gamestate=gamestate)

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
        #print(user)
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
            #print("dupe detected")
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
    #print(deck)

    if len(deck) < 30:
        return 

    saveCustomDeck(session['username'], deck)
    return redirect(url_for("index"))

@login_required
@socketio.on("deck_request_options")
def send_options():
    if "username" in session:
        print("sending options from db...")
        connection = sqlite3.connect("caravan.db")
        db = connection.cursor()
        print(f"username {session["username"]}")
        db.execute("""SELECT * FROM decks WHERE username = ?""", (session["username"],))
        decks_as_json = db.fetchone()
        #print(decks_as_json)
        if decks_as_json == None:
            return

        count = -1
        for col in decks_as_json:
            if col != None:
                count += 1
        print(count)
        
        options = []
        for deck_num in range(count):
            options.append(f"deck{deck_num+1}")
        socketio.emit("dropdown_options", options)  

@socketio.on("deck_dropdown_selection")
def handle_selection(deck):
    print(f"User selected: {deck}")
    session["preferred_deck"] = deck

@socketio.on("create_game")
def create_game():
    
    print("create game called")

    # load custom deck
    if "preferred_deck" in session:
        print(session)
        custom_deck1 = loadCustomDeck(session['username'], session['preferred_deck'])
        custom_deck2 = loadCustomDeck(session['username'], session['preferred_deck'])

        print(custom_deck1)        
        print(custom_deck2)

    else:
        custom_deck2 = False
        custom_deck1 = False

    gamestate = Game(custom_deck1, custom_deck2)
    gamestate.startGame()   
    gamestate.game_started = True
    gamestate.gametype = "singleplayer"
    game_id = ''.join([str(random.randint(0, 9)) for i in range(5)])
    gamestate.game_id = game_id
    active_games.append([gamestate, game_id])  
    gamestate.getValues()

    # Add this line to send the initial game state
    response_data = gamestate.to_dict()
    emit("game_update", response_data)
    
    # Then redirect
    emit("redirect", {"url": f"/game/{game_id}"})

@login_required
@socketio.on("create_multiplayer_game")
def create_multiplayer_game():
    game_id = ''.join([str(random.randint(0, 9)) for i in range(5)])
    game_info = [True, session["username"], None, "multiplayer"]  # waiting_for_player, player1 username, player2 username
    
    gamestate = None
    if "preferred_deck" in session:
        active_games.append([gamestate, game_id, game_info, (session["username"], session["preferred_deck"])])
    else:
        active_games.append([gamestate, game_id, game_info])

    
    join_room(game_id)

    # Redirect the client
    emit("redirect", {"url": f"/game/{game_id}"})

@login_required
@socketio.on("join_multiplayer_game")
def join_multiplayer_game(data):
    game_id = data['game_id']

    for game in active_games:
        if game[1] == game_id and game[2][0] == True:
            # Join this socket to the game room
            
            game[2][2] = session["username"]  # Set player2 username
            
            if len(game) > 3:
                custom_deck1 = loadCustomDeck(*game[3])
                print("player 1 deck - ", custom_deck1)
            else:
                custom_deck1 = False

            if "preferred_deck" in session:
                custom_deck2 = loadCustomDeck(session["username"], session["preferred_deck"])
                print("player 2 deck - ", custom_deck2)

            else:
                custom_deck2 = False
            # Check if players have preferred decks
            # (This part could be improved depending on your exact implementation)

            print(custom_deck1, custom_deck2)
            
            gamestate = Game(custom_deck1, custom_deck2)
            gamestate.startGame()
            gamestate.player1 = game[2][1]  # Get player1 from game_info
            gamestate.player2 = session["username"]
            gamestate.game_started = True
            gamestate.gametype = "multiplayer"
            gamestate.game_id = game_id
            gamestate.waiting_for_player = False
            gamestate.getValues()
            
            game[0] = gamestate

            join_room(game_id)

            # Notify all clients in the room about the game update
            response_data = gamestate.to_dict()
            emit("game_update", response_data, room=game_id)
            
            # Emit a specific event for the waiting player
            emit("game_joined", {"game_id": game_id}, broadcast=True)
            
            # Redirect both players
            emit("redirect", {"url": f"/game/{game_id}"}, room=game_id)
            return
            
    # Game not found or already full
    emit("game_error", {"message": "Game not found or already full"})

@app.route("/game/<game_id>")
def game_page(game_id):
    print("game page route loaded")
    # Check if the game exists
    for game in active_games:
        if game[1] == game_id:
            gamestate = game[0]

            print(gamestate)
            
            if gamestate and gamestate.gametype == "multiplayer":
                return render_template("multiplayer.html", game_id=game_id, gamestate=gamestate, current_user=session["username"])
            elif gamestate and gamestate.gametype == "singleplayer":
                return render_template("singleplayer.html", game_id=game_id, gamestate=gamestate, current_user=session["username"])
            elif gamestate and gamestate.gametype == "AI":
                return render_template("AI.html", game_id=game_id, gamestate=gamestate, current_user=session["username"])
            elif not gamestate:
                # This is for waiting in multiplayer lobby
                return render_template("waiting_room.html", game_id=game_id)
                
    # Game not found, redirect to index
    return redirect(url_for("index"))


@socketio.on("request_game_state")
def request_game_state(data):
    game_id = data.get('game_id')

    print("gamestate request recieved for ", game_id)
    
    print(active_games)
    # Find the game in active_games
    for game in active_games:
        if game[1] == game_id:
            gamestate = game[0]
    if gamestate:
        response_data = gamestate.to_dict()

        print("\n\n response data ", response_data, "\n\n")
        print("emmiting game update")
        emit("game_update", response_data)
    else:
        emit("error", {"message": "Game not found"})


@socketio.on('join_game_room')
def on_join_game_room(data):
    game_id = data['game_id']
    # Find the game and send its current state
    for game in active_games:
        if game[1] == game_id:
            gamestate = game[0]
            if gamestate:
                response_data = gamestate.to_dict()
                emit("game_update", response_data)

@socketio.on('cancel_room_button')
def cancel_room_button(data):
    game_id = data['game_id']
    
    # Find the game and send its current state
    for game in active_games:
        if game[1] == game_id:
            active_games.remove(game)
            return redirect(url_for("index"))

@login_required
@socketio.on("create_game_ai")
def create_game_ai():

    print("create AI game called")

    # load custom deck
    if "preferred_deck" in session:
        print(session)
        custom_deck1 = loadCustomDeck(session['username'], session['preferred_deck'])
        custom_deck2 = loadCustomDeck(session['username'], session['preferred_deck'])

    else:
        custom_deck2 = False
        custom_deck1 = False

    gamestate = Game(custom_deck1, custom_deck2)
    gamestate.startGame()   
    gamestate.game_started = True
    gamestate.gametype = "AI"
    game_id = ''.join([str(random.randint(0, 9)) for i in range(5)])
    gamestate.game_id = game_id
    active_games.append([gamestate, game_id])  
    gamestate.getValues()

    # Add this line to send the initial game state

    response_data = gamestate.to_dict()
    emit("game_update", response_data)
    
    # Then redirect
    emit("redirect", {"url": f"/game/{game_id}"})

@socketio.on("place_card")
def handle_place_card(data):
    hand_index = data["hand_index"]
    caravan_index = data["caravan_index"]
    game_id = data['game_id']
    #print(game_id)

    game_found = False
    for game in active_games:
        print(active_games)
        if game[1] == game_id:
            gamestate = game[0]
            print("game found, setting gamestate...")
            game_found = True
    if game_found == False:
        print("game not found in active_games", active_games, game_id)
        return

    if not gamestate:
        #print("no gamestate, returning..")
        return
    
    if hand_index is None or caravan_index is None:
        return
    

    #print(gamestate)

    # Determine player based on hand index
    if gamestate.gametype == "singleplayer" or gamestate.gametype == "AI":
        if hand_index < 8:
            player = "1"
        else:
            player = "2"
            hand_index -= 8  # Adjust index for player 2's hand

    # DETERMINE IF IT IS GAME VS AI, IF IT IS, PREVENT PLAYER 2 FROM MAKING A MOVE
    if gamestate.gametype == "AI":
        if player == "2":
            return
        if gamestate.checkForWin() != "":
            print("game is over, returning")
            return
    
    # MULTIPLAYER GAMES
    if gamestate.gametype == "multiplayer":
        if gamestate.player1 == session["username"]:
            player = "1"
            #print(f"setting player to 1")
            if hand_index > 7:
                return

            
        elif gamestate.player2 == session["username"]:
            #print(f"setting player to 2")
            player = "2"
            if hand_index <= 7:
                return
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

        
    
    if player == gamestate.getTurn() and gamestate.numturns > 5 and (placed_card_value1 != 11) and (placed_card_value1 != 13) and (placed_card_value2 != 11) and (placed_card_value2 != 13) and (placed_card_value1 != 12) and (placed_card_value2 != 12):
    
        # Make sure the index is valid
        if player == "1" and hand_index < len(gamestate._hand1.getHand()):
            valid_move = False
            # If no direction is set yet
            if direction1 is None:
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
                gamestate.placeCard(player, hand_index, caravan_index)
                gamestate.flipTurn()
                gamestate._hand1.replenishHand()

        elif player == "2" and hand_index < len(gamestate._hand2.getHand()):
            valid_move = False
            
            # If no direction is set yet
            if not direction2:
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
                #print(f"valid move player: {player}")


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
                print("flipping turn")
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
    

    gamestate.handleDirectionsSuits()
    print("dirs suits after place normal card")
    print(f"cars1 dir: {gamestate._caravans1_direction}")
    print(f"cars2 dir: {gamestate._caravans2_direction}")

    gamestate.getValues()

    # Include gamestate.win_status in the response
    response_data = gamestate.to_dict()
    response_data['player'] = player
    
    # Send updated game state to all clients
    #print("Sending game_update:", response_data)

    emit("game_update", response_data, broadcast=True)

@socketio.on("discard_card")
def handle_discard_card(data):
    print("discard card called")
    hand_index = data["hand_index"]

    game_id = data['game_id']

    game_found = False
    for game in active_games:
        print(active_games)
        if game[1] == game_id:
            gamestate = game[0]
            print("game found, setting gamestate...")
            game_found = True
    if game_found == False:
        print("game not found in active_games", active_games, game_id)
        return


    if not gamestate:
        print("no gamestate, returning...")
        return        

    # Determine player based on hand index
    if gamestate.gametype == "singleplayer" or gamestate.gametype == "AI":
        if hand_index < 8:
            player = "1"
        else:
            player = "2"
            hand_index -= 8  # Adjust index for player 2's hand

    # DETERMINE IF IT IS GAME VS AI, IF IT IS, PREVENT PLAYER 2 FROM MAKING A MOVE
    if gamestate.gametype == "AI":
        if player == "2":
            return
        
    # MULTIPLAYER GAMES
    if gamestate.gametype == "multiplayer":
        if gamestate.player1 == session["username"]:
            player = "1"
            #print(f"setting player to 1")
            if hand_index > 7:
                return

            
        elif gamestate.player2 == session["username"]:
            #print(f"setting player to 2")
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
        
        if gamestate.numturns > 5:
            gamestate.flipTurn()

    
    
    # Send updated game state to all clients
    emit("game_update", gamestate.to_dict(), broadcast=True)

@socketio.on("place_side_card")
def place_side_card(data): 
    game_id = data['game_id']

    for game in active_games:
        if game[1] == game_id:
            gamestate = game[0]
        else:
            return

    if not gamestate:
        return
    if gamestate.numturns < 5:
        return

    hand_index = data["hand_index"]
    caravan_card_index = data["caravan_card_index"]
    caravan_index = data["caravan_index"]

    if hand_index is None or caravan_index is None or caravan_card_index is None:
        return

    # Determine player based on hand index
    if gamestate.gametype == "singleplayer" or gamestate.gametype == "AI":
        if hand_index < 8:
            player = "1"
        else:
            player = "2"
            hand_index -= 8  # Adjust index for player 2's hand

    # DETERMINE IF IT IS GAME VS AI, IF IT IS, PREVENT PLAYER 2 FROM MAKING A MOVE
    if gamestate.gametype == "AI":
        if player == "2":
            return
        
     # MULTIPLAYER GAMES
    if gamestate.gametype == "multiplayer":
        if gamestate.player1 == session["username"]:
            player = "1"
            #print(f"setting player to 1")

            
        elif gamestate.player2 == session["username"]:
            #print(f"setting player to 2")
            player = "2"
            hand_index -= 8
    
    if player != gamestate.getTurn():
        return


    placed_card_value = gamestate._hand1.getHand()[hand_index].value() if player == "1" else gamestate._hand2.getHand()[hand_index].value()

    # Allow players to place K/J on either their own or opponent's caravans
    target_caravan_index = caravan_index if caravan_index < 3 else caravan_index - 3  # Convert to 0-2 range
    player_caravans = caravan_index < 3  # True if targeting player 1's caravans
    target_caravan = gamestate._board.getCaravan1()[target_caravan_index] if player_caravans else gamestate._board.getCaravan2()[target_caravan_index]
    if not target_caravan or caravan_card_index >= len(target_caravan):
        #print("Invalid target caravan or card index")
        return
    
    print(placed_card_value)

    if placed_card_value in [11, 12, 13]:  # If it's a J or K
        # Use 0-5 range for caravans in bonus cards (0-2 for player 1, 3-5 for player 2)
        bonus_caravan_index = target_caravan_index if player_caravans else target_caravan_index + 3
        
         # FLIP FOR QUEEN
        if placed_card_value == 12:

            if bonus_caravan_index > 2:
                queen_flip_player = "2"
            else:
                queen_flip_player = "1"

            # return if top card is not the the target card
            if caravan_card_index != len(target_caravan)-1:
                    return
            if player_caravans: #p1
                # Get the queen's suit to update the caravan suit
                queen_suit = gamestate._hand1.getHand()[hand_index].getSuit()
                # Update the suit for the caravan
                gamestate._caravans1_suit[target_caravan_index] = queen_suit
                        # Flip the direction
                gamestate.flipOrder(target_caravan_index, queen_flip_player)

            else: #p2
                queen_suit = gamestate._hand2.getHand()[hand_index].getSuit()
                gamestate._caravans2_suit[target_caravan_index] = queen_suit
                gamestate.flipOrder(target_caravan_index, queen_flip_player)

        elif placed_card_value == 11:
            if caravan_index < 3:
                target_player = "1"
            else:
                target_player = "2"
            gamestate._board.removeCard(target_player, target_caravan_index, caravan_card_index)
            for card in gamestate.bonus_cards:
                if card[1] == target_caravan_index and card[2] == caravan_card_index:
                    gamestate.bonus_cards.remove(card)


        if placed_card_value != 11:
            gamestate.bonus_cards.append([placed_card_value, bonus_caravan_index, caravan_card_index])  

        if player == "1":
            gamestate._hand1.removeCard(hand_index)
            gamestate._hand1.replenishHand()

        else:
            gamestate._hand2.removeCard(hand_index)
            gamestate._hand2.replenishHand()

        gamestate.flipTurn()

    else: 
        print("not a K or J, rejecting...")

    
    gamestate.handleDirectionsSuits()
    print("dirs suits after place side card")
    print(f"cars1 dir: {gamestate._caravans1_direction}")
    print(f"cars2 dir: {gamestate._caravans2_direction}")

    #print("CARAVAN BONUSES", gamestate.bonus_cards)

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

        #print(f"Caravan values 1: {gamestate.caravan_values1}")
        #print(f"Caravan values 2: {gamestate.caravan_values2}")
        
        # Send updated game state to all clients
        #print("Sending game_update:", response_data)
        emit("game_update", response_data, broadcast=True)
        
    except Exception as e:
        #print(f"Error during side card placement: {e}")
        # If there's an error, provide feedback
        emit("game_update", {"error": "An error occurred during side card placement."}, broadcast=True)

@socketio.on("make_ai_move")
def make_ai_move(data):
    game_id = data
    print("game id", game_id)
    print("game id type", type(game_id))

    print("\n starting ai move \n ")

    game_found = False
    for game in active_games:
        if game[1] == game_id:
            gamestate = game[0]
            game_found = True
    if game_found == False:
        print("game not found in active_games", active_games, game_id)
        return
        
    if not gamestate:
        print("no gamestate in ai, returning...")
        return

    if gamestate.getTurn() != "2":
        return
    
    timeout_counter = 0
    valid_move = False
    while (not valid_move) and timeout_counter < 50:
        timeout_counter += 1
        print(timeout_counter)
        caravan_index = random.randint(0, 2)
        hand_index = random.randint(0, len(gamestate._hand2.getHand())-1) if gamestate._hand2.getHand() else 0

        # Only try to access caravan card index if the caravan has cards
        if len(gamestate._board.getCaravan2()[caravan_index]) > 0:
            caravan_card_index = random.randint(0, len(gamestate._board.getCaravan2()[caravan_index])-1)
        else:
            caravan_card_index = 0       
        player = "2"

        # make sure we have cards in the hand
        if not gamestate._hand2.getHand():
            break

        #print(f"\n\ncaravan index: {caravan_index}, hand_index: {hand_index}, caravan card index {caravan_card_index}\n\n\ ")

        placed_card_value2 = gamestate._hand2.getHand()[hand_index].value() 
        top_card_value2 = gamestate._board._caravans2[caravan_index][-1].value() if gamestate._board._caravans2[caravan_index] else None
        direction2 = gamestate._caravans2_direction[caravan_index][0] if (gamestate._caravans2_direction[caravan_index] and isinstance(gamestate._caravans2_direction[caravan_index], list)) else None
        top_card_suit2 = gamestate._board._caravans2[caravan_index][-1].getSuit() if gamestate._board._caravans2[caravan_index] else None
        placed_card_suit2 = gamestate._hand2.getHand()[hand_index].getSuit()

        # HANDLE PLACING KINGS JACKS (AND QUEENS)

        if gamestate.numturns > 5 and (placed_card_value2 == 11 or placed_card_value2 == 13 or placed_card_value2 == 12):

            # Allow players to place K/J on either their own or opponent's caravans
            target_caravan_index = random.randint(0, 2)  # Always 0, 1, or 2
            bonus_caravan_index = target_caravan_index + 3

            # Only add bonus card if there's at least one card in the target caravan
            target_is_player1 = target_caravan_index < 3
            target_caravan = gamestate._board.getCaravan1()[target_caravan_index] if target_is_player1 else gamestate._board.getCaravan2()[target_caravan_index - 3]

            if target_caravan and len(target_caravan) > 0:
                valid_caravan_card_index = random.randint(0, len(target_caravan) - 1)

                # FLIP FOR QUEEN
                if placed_card_value2 == 12:

                    if bonus_caravan_index > 2:
                        queen_flip_player = "2"
                    else:
                        queen_flip_player = "1"
                    #return if queen is not placed ontop card
                    if caravan_card_index != len(target_caravan)-1:
                        continue

                    if target_caravan_index >= 3:
                        target_caravan_index = target_caravan_index % 3  # Convert to 0, 1, or 2
                    
                    queen_suit = gamestate._hand2.getHand()[hand_index].getSuit()
                    gamestate._caravans2_suit[target_caravan_index] = queen_suit
                    gamestate.flipOrder(target_caravan_index, queen_flip_player)

                # REMOVE FOR JACKS
                elif placed_card_value2 == 11:
                    if caravan_index < 3:
                        target_player = "1"
                    else:
                        target_player = "2"
                    gamestate._board.removeCard(target_player, target_caravan_index, caravan_card_index)

                    to_remove = []
                    for i, card in enumerate(gamestate.bonus_cards):
                        if card[1] == target_caravan_index and card[2] == caravan_card_index:
                            to_remove.append(i)
                    # Remove in reverse order to avoid index shifting problems
                    for i in sorted(to_remove, reverse=True):
                        gamestate.bonus_cards.pop(i)


                if placed_card_value2 != 11:
                    gamestate.bonus_cards.append([placed_card_value2, target_caravan_index, valid_caravan_card_index]) 

                gamestate._hand2.removeCard(hand_index)
                gamestate.flipTurn()
                gamestate._hand1.replenishHand()
                valid_move = True

        elif gamestate.numturns > 5 and (placed_card_value2 != 11) and (placed_card_value2 != 13) and (placed_card_value2 != 12):
            valid_move = False    
            # If no direction is set yet
            if not direction2:
                valid_move = True
            elif placed_card_value2 > 10:
                valid_move = True
            # if there is no top card, move is always valid
            elif top_card_suit2 == None or top_card_value2 == None:
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
                gamestate.placeCard(player, hand_index, caravan_index)
                gamestate.flipTurn()
                gamestate._hand2.replenishHand()
            else:
                print(f"Invalid move: card: {placed_card_value2}, caravan {caravan_index}")

        elif gamestate.numturns < 6:
            # OPENING ROUND 3 TURNS EACH
            if hand_index < len(gamestate._hand2.getHand()) and placed_card_value2 < 11:
                # Find the first unfilled caravan for player 2 (indices 3, 4, 5)
                unfilled_caravans = [i for i in range(3, 6) if not gamestate.opening_round_filled[i]]
                
                if unfilled_caravans and caravan_index == unfilled_caravans[0] - 3:
                    gamestate.opening_round_filled[caravan_index+3] = True
                    gamestate.placeCard(player, hand_index, caravan_index)
                    gamestate.flipTurn()
                    valid_move = True

    gamestate.handleDirectionsSuits()
    print("dirs suits after place AI card")
    print(f"cars1 dir: {gamestate._caravans1_direction}")
    print(f"cars2 dir: {gamestate._caravans2_direction}")
    
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

        #print(f"Caravan values 1: {gamestate.caravan_values1}")
        #print(f"Caravan values 2: {gamestate.caravan_values2}")
        
        # Send updated game state to all clients
        #print("Sending game_update:", response_data)
        
        # Send updated game state to all clients

        time.sleep(2)
        print("emmitting game update", gamestate.current_turn)
        emit("game_update", response_data, room=game_id)
        
    except Exception as e:
        #print(f"Error during AI move: {e}")
        # If there's an error, redirect to the index page or reset the game
        emit("game_update", {"error": "An error occurred. Starting a new game."}, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)