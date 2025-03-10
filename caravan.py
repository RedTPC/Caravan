import random

initial_hand_size = 8
final_hand_size = 5
value_dict = {"A" : 1, "2" : 2, "3" : 3, "4" : 4, "5" : 5, "6" : 6, "7" : 7, "8" : 8, "9" : 9, "10" : 10, "J" : 11, "Q" : 12, "K" : 13}


class Card():
    def __init__(self, suit, face):
        self._suit = suit
        self._face = face

    def getFace(self):
        return self._face

    def getSuit(self):
        return self._suit
    
    def value(self):
        return value_dict[self._face]
    
    def to_dict(self):
        return {"suit": self._suit, "face": self._face}
    
    def __str__(self):
        #return f"Suit: {self._suit}, Face: {self._face}"
        return self._face + self._suit

class Deck():
    def __init__(self):
        self._deck = []

    def shuffle(self):
        random.shuffle(self._deck)
    
    def populateDeck(self):
        suits = ["♥", "♦", "♠", "♣"]
        faces = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

        for suit in suits:
            for face in faces:
                
                self._deck.append(Card(suit, face))

    def popCard(self):
        top_card = self._deck[0]
        self._deck.pop(0)
        return top_card

    def __str__(self):
        output = ""
        for i in self._deck:
            output += str(i)
        return output

class Board:
    def __init__(self):
        self._caravans1 = [[], [], []]
        self._caravans2 = [[], [], []]
        self._caravans1_info = [] # each caravan has a direction
        self._caravans2_info = [] 
    
    def getCaravan1(self):
        return self._caravans1
    
    def getCaravan2(self):
        return self._caravans2
    
    def addCard(self, player, card, caravan):
        if player == "1":
            self._caravans1[caravan].append(card)

        elif player == "2":
            self._caravans2[caravan].append(card)

        
    def toDict(self):
        # Convert the caravans to a serializable format (list of cards)
        caravan1 = [[str(card) for card in caravan] for caravan in self._caravans1]
        caravan2 = [[str(card) for card in caravan] for caravan in self._caravans2]

        # Convert the board to a dictionary format
        return {
            'caravans1': caravan1,
            'caravans2': caravan2,
            'caravans1_info': self._caravans1_info,
            'caravans2_info': self._caravans2_info
        }
    
    def __str__(self):
        output = "Caravan 1:\n"
        for i, caravan in enumerate(self._caravans1, start=1):
            output += f"  Caravan {i}: " + ", ".join(str(card) for card in caravan) + "\n"
        
        output += "\nCaravan 2:\n"
        for i, caravan in enumerate(self._caravans2, start=1):
            output += f"  Caravan {i}: " + ", ".join(str(card) for card in caravan) + "\n"
        return output
    
class Hand():
    def __init__(self, deck):
        self._hand = []
        self._deck = deck
    
    def populateHand(self):
        for i in range(initial_hand_size):
            self._hand.append(self._deck.popCard())
    
    def replenishHand(self):
        missing_cards = final_hand_size - len(self._hand)
        for i in range(missing_cards):
            self._hand.append(self._deck.popCard()) 
    
    def removeCard(self, index):
        self._hand.pop(index)
    
    def getHand(self):
        return self._hand
    
    def to_dict(self):
        return {"hand": [card.to_dict() for card in self._hand]}
    
    def __str__(self):
        return ', '.join(str(card) for card in self._hand)

class Game:
    def __init__(self):
        self._board = Board()
        self._deck1 = Deck()
        self._deck2 = Deck()
        self._deck1.populateDeck()
        self._deck2.populateDeck()
        self._hand1 = Hand(self._deck1)
        self._hand2 = Hand(self._deck2)
        self._caravan_status = [None, None, None] # contains the winning bids
        self._caravans1_direction = [None, None, None]
        self._caravans2_direction = [None, None, None]
        self._caravans1_suit = [None, None, None]
        self._caravans2_suit = [None, None, None]
        self._discard_pile1 = []
        self._discard_pile2 = []
        self._turn = "1"
        self.numturns = 0
        self._bonus_cards = [] # list of lists (card, caravan_index 1-6, caravan_card_index)

    def ShuffleDecks(self):
        self._deck1.shuffle()
        self._deck2.shuffle()

    def startGame(self):
        self.ShuffleDecks()
        self._hand1.populateHand()
        self._hand2.populateHand()
        # self.openingRound()
    
    def getTurn(self):
        return str(self._turn)
    
    def flipTurn(self):
        self.numturns += 1
        if self._turn == "1":
            self._turn = "2"
        else:
            self._turn = "1"
        print(f"flipping turn to {self._turn}")

    def flipOrder(self, caravan_index):
        if self._turn == "1":
            # Check if direction is None or not a list
            if self._caravans1_direction[caravan_index] is None or not isinstance(self._caravans1_direction[caravan_index], list):
                # Default to descending if no direction set yet
                self._caravans1_direction[caravan_index] = ["DESC", 0]
            elif self._caravans1_direction[caravan_index][0] == "ASC":
                self._caravans1_direction[caravan_index][0] = "DESC"
            else:
                self._caravans1_direction[caravan_index][0] = "ASC"
        elif self._turn == "2":
            # Check if direction is None or not a list
            if self._caravans2_direction[caravan_index] is None or not isinstance(self._caravans2_direction[caravan_index], list):
                # Default to descending if no direction set yet
                self._caravans2_direction[caravan_index] = ["DESC", 0]
            elif self._caravans2_direction[caravan_index][0] == "ASC":
                self._caravans2_direction[caravan_index][0] = "DESC"
            else:
                self._caravans2_direction[caravan_index][0] = "ASC"

    def placeCard(self, player, hand_index, caravan_index):
        if player == "1":
            card = self._hand1.getHand()[hand_index]
            self._hand1.removeCard(hand_index)
            self._board.addCard("1", card, caravan_index)

        elif player == "2":
            card = self._hand2.getHand()[hand_index]
            self._hand2.removeCard(hand_index)
            self._board.addCard("2", card, caravan_index)

    def discardCard(self, player, hand_index):
        if player == "1":
            card = self._hand1.getHand()[hand_index]
            self._hand1.removeCard(hand_index)
            self._discard_pile1.append(card)
            print(f"Discard pile 1: {str(self._discard_pile1)}")
        elif player == "2":
            card = self._hand2.getHand()[hand_index]
            self._hand2.removeCard(hand_index)
            self._discard_pile2.append(card)
            print(f"Discard pile 2: {str(self._discard_pile2)}")

    def getValues(self):
        caravan_values1 = [0, 0, 0]  
        caravan_values2 = [0, 0, 0]

        for i, caravan in enumerate(self._board.getCaravan1()):
            for card in caravan:
                caravan_values1[i] += card.value() if (card.getFace() != "Q") and (card.getFace() != "K") and (card.getFace() != "J") else 0

        for i, caravan in enumerate(self._board.getCaravan2()):
            for card in caravan:
                caravan_values2[i] += card.value() if (card.getFace() != "Q") and (card.getFace() != "K") and (card.getFace() != "J") else 0

        # HANDLE KINGS AND JACKS

        # list of lists (card, caravan_index 1-6, caravan_card_index)

        print("Bonus Cards List: ")
        for bonus_card in self._bonus_cards:
            caravans1 = self._board.getCaravan1()
            caravans2 = self._board.getCaravan2()
            # bonus_card1 = caravans1[bonus_card[0]]
            # bonus_card2 = caravans2[bonus_card[0]]
            # caravan_card_index1 = caravans1[bonus_card[2]]
            # caravan_card_index2 = caravans2[bonus_card[2]]
            # caravan_index1 = caravans1[bonus_card[1]]
            # caravan_index2 = caravans2[bonus_card[1]]

            #KINGS
            print(f"\n\nBonus Card: {bonus_card[0]}, Bonus Card Info: {bonus_card}\n\n")
            
            # DOES NOT ACCOUNT FOR KINGS ONTOP OF KINGS ETC

            if bonus_card[0] == 13:  # King doubles card value
                if bonus_card[1] < 3:  # Player 1's caravans
                    caravan_values1[bonus_card[1]] += caravans1[bonus_card[1]][bonus_card[2]].value()
                elif bonus_card[1] >= 3:  # Player 2's caravans
                    caravan_values2[bonus_card[1] - 3] += caravans2[bonus_card[1] - 3][bonus_card[2]].value()

            elif bonus_card[0] == 11:  # Jack removes card value
                if bonus_card[1] < 3:
                    caravan_values1[bonus_card[1]] -= caravans1[bonus_card[1]][bonus_card[2]].value()
                elif bonus_card[1] >= 3:
                    caravan_values2[bonus_card[1] - 3] -= caravans2[bonus_card[1] - 3][bonus_card[2]].value()








        return caravan_values1, caravan_values2

    def checkForWin(self):
        values1 = self.getValues()[0]
        values2 = self.getValues()[1]
        result = [None, None, None]

        
        for i in range(3):
            if (21 <= values1[i] <= 26) and (21 > values2[i] or values2[i] > 26):
                result[i] = "p1"
            
            elif (21 <= values2[i] <= 26) and (21 > values1[i] or values1[i] > 26):
                result[i] = "p2"

            elif (21 > values1[i] or values1[i] > 26) and (21 > values2[i] or values2[i] > 26):
                result[i] = None

            elif (21 <= values2[i] <= 26) and (21 <= values1[i] <= 26):

                if values1[i] > values2[i]:
                    result[i] = "p1"

                elif values2[i] > values1[i]:
                    result[i] = "p2"
        
        # replaces current final caravan status with the results only if the caravan has not already been sold and there is a new winner
        for i in range(3):
            if result[i] is not None and self._caravan_status[i] is None:
                self._caravan_status[i] = result[i]

        p1count = 0
        p2count = 0   
        for i in self._caravan_status:
            if i == "p1":
                p1count += 1
            elif i == "p2":
                p2count += 1
        if p1count >= 2:
            return "p1"
        elif p2count >= 2:
            return "p2"
        else: 
            print(f"neither player won p1:{p1count}, p2:{p2count}")
            print(self._caravan_status)
            print(self._board)

            return ""
        

    def handleDirectionsSuits(self):
        # PLAYER 1
        number_cards1 = [[], [], []]
        for i, caravan in enumerate(self._board.getCaravan1()):
            for card in caravan:
                if card.getFace() != "K" and card.getFace() != "Q" and card.getFace() != "J":
                    number_cards1[i].append(card)
            
        
        for i, caravan in enumerate(number_cards1):
            # MAKE SURE IT ISNT A QUEEN
            if len(caravan) > 1 and (caravan[-1].getFace() != "Q") and (caravan[-2].getFace() != "Q"):
                if caravan[-1].value() > caravan[-2].value():
                    self._caravans1_direction[i] = ["ASC", caravan[-1].value()]
                elif caravan[-1].value() < caravan[-2].value():
                    self._caravans1_direction[i] = ["DESC", caravan[-1].value()]

            # SUITS
        for i, caravan in enumerate(self._board.getCaravan1()):
            if len(caravan) > 0:
                self._caravans1_suit[i] = self._board.getCaravan1()[i][-1].getSuit()

        
    
        # Handle suits based on the last card of each caravan, including queens
        for i, caravan in enumerate(self._board.getCaravan1()):
            if len(caravan) > 0:
                self._caravans1_suit[i] = self._board.getCaravan1()[i][-1].getSuit()
                
                # If the last card is a queen, it changes the direction as well
                if caravan[-1].getFace() == "Q":
                    if self._caravans1_direction[i] is None or not isinstance(self._caravans1_direction[i], list):
                        self._caravans1_direction[i] = ["DESC", 0]
                    elif self._caravans1_direction[i][0] == "ASC":
                        self._caravans1_direction[i][0] = "DESC"
                    else:
                        self._caravans1_direction[i][0] = "ASC"
        
        # Similar for player 2
        for i, caravan in enumerate(self._board.getCaravan2()):
            if len(caravan) > 0:
                self._caravans2_suit[i] = self._board.getCaravan2()[i][-1].getSuit()
                
                # If the last card is a queen, it changes the direction as well
                if caravan[-1].getFace() == "Q":
                    if self._caravans2_direction[i] is None or not isinstance(self._caravans2_direction[i], list):
                        self._caravans2_direction[i] = ["DESC", 0]
                    elif self._caravans2_direction[i][0] == "ASC":
                        self._caravans2_direction[i][0] = "DESC"
                    else:
                        self._caravans2_direction[i][0] = "ASC"

 

        # PLAYER 2
        number_cards2 = [[], [], []]
        for i, caravan in enumerate(self._board.getCaravan2()):
            for card in caravan:
                if card.getFace() != "K" and card.getFace() != "Q" and card.getFace() != "J":
                    number_cards2[i].append(card)
        
        for i, caravan in enumerate(number_cards2):
             # MAKE SURE IT ISNT A QUEEN
            if len(caravan) > 1 and (caravan[-1].getFace() != "Q") and (caravan[-2].getFace() != "Q"):
                if caravan[-1].value() > caravan[-2].value():
                    self._caravans2_direction[i] = ["ASC", caravan[-1].value()]
                elif caravan[-1].value() < caravan[-2].value():
                    self._caravans2_direction[i] = ["DESC", caravan[-1].value()]

        # SUITS
        for i, caravan in enumerate(self._board.getCaravan2()):
            if len(caravan) > 0:
                self._caravans2_suit[i] = self._board.getCaravan2()[i][-1].getSuit()

        print(f"Directions: {self._caravans1_direction, self._caravans2_direction}, Suits: {self._caravans1_suit, self._caravans2_suit}")   


                
        
        
    def to_dict(self):
        # Return a simplified version of the game state as a dictionary
        return {
            'caravan_status': self._caravan_status,
            'hand1': self._hand1.to_dict(),
            'hand2': self._hand2.to_dict(),
            'board': self._board.toDict(),
            'discard_pile1': [card.to_dict() for card in self._discard_pile1],
            'discard_pile2': [card.to_dict() for card in self._discard_pile2],
            # 'bonus_cards': {item[0]: item[1:] for item in self._bonus_cards}
            'bonus_cards': self._bonus_cards

        }
                
    
    def __str__(self):
        return str(self._board) + "\n" + str(self._hand1) + str(self._hand2)





if __name__ == "__main__":
    mygame = Game()
    print(mygame)
    mygame.startGame()
    print(mygame)

    

    mygame.placeCard("1", 1, 1)
    mygame.placeCard("1", 2, 1)
    mygame.placeCard("1", 3, 1)
    mygame.placeCard("1", 4, 1)

    mygame.placeCard("2", 1, 1)
    mygame.placeCard("2", 2, 1)
    mygame.placeCard("2", 3, 1)
    mygame.placeCard("2", 4, 1)

    print(mygame.getValues())


    print(mygame)
    
    print(mygame.checkForWin())