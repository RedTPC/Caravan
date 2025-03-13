import sqlite3

def loadCustomDeck(username):
    connection = sqlite3.connect("app.db")
    db = connection.cursor()
    db.execute("""SELECT deck1 FROM decks WHERE username = ?""", (username,))
    deck = db.fetchall()

    if deck is None:
        print(f"No deck found for: {username} at deck1")
        return
        
    return deck

def saveCustomDeck(username, deck):

    connection = sqlite3.connect("app.db")
    db = connection.cursor()
    db.execute("""INSERT OR REPLACE INTO decks (username, deck1) VALUES (?, ?)""", (username, deck))
    connection.commit()

    if deck is None:
        print(f"No deck found for: {username}")
        return
        
    return deck