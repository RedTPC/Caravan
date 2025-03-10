from flask import Flask, render_template, url_for, redirect
from flask_socketio import SocketIO, emit
from forms import LoginForm, RegisterForm
import caravan
from caravan import Game
import random
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")
gamestate = None


@app.route("/")
def index():
    return render_template("index.html", gamestate=gamestate)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        return redirect(url_for("index"))

    else:
        return render_template("login.html", form=form)
    
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        return redirect(url_for("login"))

    else:
        return render_template("register.html", form=form)

@socketio.on("create_game")
def create_game():
    global gamestate
    gamestate = Game()
    gamestate.startGame()

    # Initialize with zero values since no cards are played yet
    caravan_values1, caravan_values2 = [0, 0, 0], [0, 0, 0]
    
    response_data = gamestate.to_dict()
    response_data['caravan_values1'] = caravan_values1
    response_data['caravan_values2'] = caravan_values2

    emit("game_update", response_data, broadcast=True)

@socketio.on("create_game_ai")
def create_game():
    global gamestate
    gamestate = Game()
    gamestate.startGame()
    gamestate._is_vs_ai = True

    # Initialize with zero values since no cards are played yet
    caravan_values1, caravan_values2 = [0, 0, 0], [0, 0, 0]
    
    response_data = gamestate.to_dict()
    response_data['caravan_values1'] = caravan_values1
    response_data['caravan_values2'] = caravan_values2
    response_data['is_vs_ai'] = True
 
    emit("game_update", response_data, broadcast=True)


@socketio.on("place_card")
def handle_place_card(data):
    global gamestate
    if not gamestate:
        return

    hand_index = data["hand_index"]
    caravan_index = data["caravan_index"]


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
    

    caravan_values1, caravan_values2 = gamestate.getValues()

    # Include gamestate.win_status in the response
    response_data = gamestate.to_dict()
    response_data['win_status'] = gamestate.win_status
    response_data['caravan_values1'] = caravan_values1
    response_data['caravan_values2'] = caravan_values2
    response_data['is_vs_ai'] = gamestate._is_vs_ai
    response_data['player'] = player
    response_data['current_turn'] = gamestate.getTurn()  


    print(f"Caravan values 1: {caravan_values1}")
    print(f"Caravan values 2: {caravan_values2}")
    
    # Send updated game state to all clients
    print("Sending game_update:", response_data)

    emit("game_update", response_data, broadcast=True)

@socketio.on("discard_card")
def handle_discard_card(data):
    global gamestate
    if not gamestate:
        return
    
    if gamestate.numturns < 6:
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
        
    
    # Determine player based on who sent the request
    if player == gamestate.getTurn() and gamestate.numturns > 5:
    
        # Make sure it's the player's turn and the hand index is valid
        if player == "1" and hand_index < len(gamestate._hand1.getHand()):
            gamestate.discardCard(player, hand_index)
            gamestate.flipTurn()
            gamestate._hand1.replenishHand()
        elif player == "2" and hand_index < len(gamestate._hand2.getHand()):
            gamestate.discardCard(player, hand_index)
            gamestate.flipTurn()
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
    if hand_index < 8:
        player = "1"
    else:
        player = "2"
        hand_index -= 8  # Adjust index for player 2's hand

    # DETERMINE IF IT IS GAME VS AI, IF IT IS, PREVENT PLAYER 2 FROM MAKING A MOVE
    if gamestate._is_vs_ai == True:
        if player == "2":
            return
        

    placed_card_value = gamestate._hand1.getHand()[hand_index].value() if player == "1" else gamestate._hand2.getHand()[hand_index].value()

    # Allow players to place K/J on either their own or opponent's caravans
    target_caravan_index = caravan_index if player == "1" else caravan_index + 3  # Player 2's caravans are indexed 3-5


    if placed_card_value in [11, 13]:  # If it's a J or K
        gamestate._bonus_cards.append([placed_card_value, target_caravan_index, caravan_card_index])  
        if player == "1":
            gamestate._hand1.removeCard(hand_index)
        else:
            gamestate._hand2.removeCard(hand_index)

        gamestate.flipTurn()
        gamestate._hand2.replenishHand() if player == "1" else gamestate._hand1.replenishHand()

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

    caravan_values1, caravan_values2 = gamestate.getValues()

    # Include gamestate.win_status in the response
    response_data = gamestate.to_dict()
    response_data['win_status'] = gamestate.win_status
    response_data['caravan_values1'] = caravan_values1
    response_data['caravan_values2'] = caravan_values2
    response_data['is_vs_ai'] = gamestate._is_vs_ai
    response_data['player'] = player
    response_data['current_turn'] = gamestate.getTurn()  



    print(f"Caravan values 1: {caravan_values1}")
    print(f"Caravan values 2: {caravan_values2}")
    
    # Send updated game state to all clients
    print("Sending game_update:", response_data)


    # IF ITS NOT A KING OR JACK, REMOVE CARAVANCARDINDEX AND REDIRECT TO MAIN PLACE CARD
    # GOOD IDEA!

        
    
    # Send updated game state to all clients
    emit("game_update", response_data, broadcast=True)


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
        hand_index = random.randint(0, 4)
        caravan_card_index = random.randint(0, len(gamestate._board.getCaravan2()[caravan_index])-1) if len(gamestate._board.getCaravan2()[caravan_index]) > 0 else None
        player = "2"

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
            gamestate._bonus_cards.append([placed_card_value2, target_caravan_index, caravan_card_index])  
            gamestate._hand2.removeCard(hand_index)
            gamestate.flipTurn()
            gamestate._hand1.replenishHand()

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

        caravan_values1, caravan_values2 = gamestate.getValues()

    except:
        index_url = url_for("/")
        emit("redirect", {"url": index_url})   

    response_data = gamestate.to_dict()
    response_data['win_status'] = gamestate.win_status
    response_data['caravan_values1'] = caravan_values1
    response_data['caravan_values2'] = caravan_values2
    response_data['is_vs_ai'] = gamestate._is_vs_ai
    response_data['player'] = player
    response_data['current_turn'] = gamestate.getTurn()  


    print(f"Caravan values 1: {caravan_values1}")
    print(f"Caravan values 2: {caravan_values2}")
    
    # Send updated game state to all clients
    print("Sending game_update:", response_data)
 
    
    # Send updated game state to all clients
    emit("game_update", gamestate.to_dict(), broadcast=True)

if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)