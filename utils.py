import sqlite3
import json

def loadCustomDeck(username, deck_number):
    # takes deck number as "deck1"
    print(f"deck number: {deck_number}, username: {username}")
    connection = sqlite3.connect("caravan.db")
    db = connection.cursor()
    db.execute(f"""SELECT {deck_number} FROM decks WHERE username = ?;""", (username,))
    deck_as_json = db.fetchone()

    print(f"deck as json: {deck_as_json}")

    if deck_as_json is None:
        print(f"No deck found for: {username} at deck1")
        return
    
    deck = json.loads(deck_as_json[0])

    print("loadcustomdeck returning", deck)
    return deck

def saveCustomDeck(username, deck):
    deck_as_json = json.dumps(deck)
    connection = sqlite3.connect("caravan.db")
    db = connection.cursor()

    db.execute("""SELECT * FROM decks WHERE username = ?;""", (username,))
    all_decks = db.fetchone()

    if not all_decks:
        print("user not found in db")
        #make username col if not exists
        db.execute("""INSERT INTO decks (username) VALUES (?);""", (username,))
        
    db.execute("""SELECT * FROM decks WHERE username = ?;""", (username,))
    all_decks = db.fetchone()
    
    columns = ["deck1", "deck2", "deck3","deck4", "deck5", "deck6", "deck7", "deck8", "deck9", "deck10",]
    next_save = None

    for i, col in enumerate(columns, start=1):
        if all_decks[i] is None:  # Find the first empty deck slot
            next_save = col
            break

    if not next_save:
        print("No space in DB for a new deck")
        return


    db.execute(f"""UPDATE decks SET {next_save} = ? WHERE username = ?""", (deck_as_json, username))
    connection.commit()
        
    return deck