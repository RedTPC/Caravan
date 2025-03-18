import random
import sqlite3
from utils import loadCustomDeck

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

    def populateCustomDeck(self, custom_deck):
        for card_str in custom_deck:
            if len(card_str) == 3:
                self._deck.append(Card(card_str[2], card_str[0:2]))
            else:
                self._deck.append(Card(card_str[1], card_str[0]))

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
        
    def removeCard(self, player, caravan, card_index):
        if player == "1" and 0 <= caravan < len(self._caravans1) and 0 <= card_index < len(self._caravans1[caravan]):
            self._caravans1[caravan].pop(card_index)
        elif player == "2" and 0 <= caravan < len(self._caravans2) and 0 <= card_index < len(self._caravans2[caravan]):
            self._caravans2[caravan].pop(card_index)


        
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

class Game():
    def __init__(self, custom_deck1, custom_deck2):


        self._board = Board()
        self._deck1 = Deck()
        self._deck2 = Deck()

        if custom_deck1 == False:
            self._deck1.populateDeck()
        else:
            self._deck1.populateCustomDeck(custom_deck1)

        if custom_deck2 == False:
            self._deck2.populateDeck()
        else:
            self._deck2.populateCustomDeck(custom_deck2)

        self._hand1 = Hand(self._deck1)
        self._hand2 = Hand(self._deck2)
        self._caravan_status = [None, None, None] # contains the winning bids
        self._caravans1_direction = [None, None, None]
        self._caravans2_direction = [None, None, None]
        self._caravans1_suit = [None, None, None]
        self._caravans2_suit = [None, None, None]
        self.opening_round_filled = [False, False, False, False, False, False] 
        self._discard_pile1 = []
        self._discard_pile2 = []
        self._turn = "1"
        self.numturns = 0
        self.bonus_cards = [] # list of lists (card, caravan_index 1-6, caravan_card_index)
        self.win_status = ""
        self.player1 = ""
        self.player2 = ""
        self.game_id = None
        self.game_started = False
        self.caravan_values1 = [0, 0, 0]
        self.caravan_values2 = [0, 0, 0]
        self.waiting_for_player = False
        self.gametype = None

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
        #print(f"flipping turn to {self._turn}")

    def flipOrder(self, caravan_index, player):
        print(f"flip order called on caravan {caravan_index}")
        if player == "1":

            # Check if direction is None or not a list
            if self._caravans1_direction[caravan_index] is None or not isinstance(self._caravans1_direction[caravan_index], list):
                # Default to descending if no direction set yet
                self._caravans1_direction[caravan_index] = ["DESC", 0]
            elif self._caravans1_direction[caravan_index][0] == "ASC":
                print("caravan direction is ASC")
                self._caravans1_direction[caravan_index][0] = "DESC"
            else:
                self._caravans1_direction[caravan_index][0] = "ASC"
        elif player == "2":
            # Check if direction is None or not a list
            if self._caravans2_direction[caravan_index] is None or not isinstance(self._caravans2_direction[caravan_index], list):
                # Default to descending if no direction set yet
                self._caravans2_direction[caravan_index] = ["DESC", 0]
            elif self._caravans2_direction[caravan_index][0] == "ASC":
                self._caravans2_direction[caravan_index][0] = "DESC"
            else:
                self._caravans2_direction[caravan_index][0] = "ASC"

            print("caravans after flip order")
            print(self._caravans1_direction)
            print(self._caravans2_direction)

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
            #print(f"Discard pile 1: {str(self._discard_pile1)}")
        elif player == "2":
            card = self._hand2.getHand()[hand_index]
            self._hand2.removeCard(hand_index)
            self._discard_pile2.append(card)
            #print(f"Discard pile 2: {str(self._discard_pile2)}")
            
    def getValues(self):
        self.caravan_values1 = [0, 0, 0]  
        self.caravan_values2 = [0, 0, 0]

        # Calculate base values for player 1's caravans
        for i, caravan in enumerate(self._board.getCaravan1()):
            for card in caravan:
                self.caravan_values1[i] += card.value() if (card.getFace() != "Q") and (card.getFace() != "K") and (card.getFace() != "J") else 0

        # Calculate base values for player 2's caravans
        for i, caravan in enumerate(self._board.getCaravan2()):
            for card in caravan:
                self.caravan_values2[i] += card.value() if (card.getFace() != "Q") and (card.getFace() != "K") and (card.getFace() != "J") else 0

        # HANDLE KINGS AND JACKS
        caravans1 = self._board.getCaravan1()
        caravans2 = self._board.getCaravan2()
        
        #print("Bonus Cards List: ")
        for bonus_card in self.bonus_cards:
            #print(f"\n\nBonus Card: {bonus_card[0]}, Bonus Card Info: {bonus_card}\n\n")
            
            # KINGS
            if bonus_card[0] == 13:  # King doubles card value
                if bonus_card[1] < 3:  # Player 1's caravans
                    # Check if the indices are valid before accessing
                    if (0 <= bonus_card[1] < len(caravans1) and 
                        caravans1[bonus_card[1]] and  # Check if caravan exists and has cards
                        0 <= bonus_card[2] < len(caravans1[bonus_card[1]])):
                        self.caravan_values1[bonus_card[1]] += caravans1[bonus_card[1]][bonus_card[2]].value()
                else:  # Player 2's caravans (index >= 3)
                    caravan_idx = bonus_card[1] - 3
                    if (0 <= caravan_idx < len(caravans2) and 
                        caravans2[caravan_idx] and  # Check if caravan exists and has cards
                        0 <= bonus_card[2] < len(caravans2[caravan_idx])):
                        self.caravan_values2[caravan_idx] += caravans2[caravan_idx][bonus_card[2]].value()

            # JACKS
            elif bonus_card[0] == 11:  # Jack removes card value
                if bonus_card[1] < 3:  # Player 1's caravans
                    if (0 <= bonus_card[1] < len(caravans1) and 
                        caravans1[bonus_card[1]] and
                        0 <= bonus_card[2] < len(caravans1[bonus_card[1]])):
                        self.caravan_values1[bonus_card[1]] -= caravans1[bonus_card[1]][bonus_card[2]].value()
                else:  # Player 2's caravans
                    caravan_idx = bonus_card[1] - 3
                    if (0 <= caravan_idx < len(caravans2) and 
                        caravans2[caravan_idx] and
                        0 <= bonus_card[2] < len(caravans2[caravan_idx])):
                        self.caravan_values2[caravan_idx] -= caravans2[caravan_idx][bonus_card[2]].value()








        return self.caravan_values1, self.caravan_values2

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
        # for i in range(3):
        #     if result[i] is not None and self._caravan_status[i] is None:

            self._caravan_status[i] = result[i]
        print(result)

        for i in result:
            if i == None:
                ""

        p1count = 0
        p2count = 0   
        for i in self._caravan_status:
            if i == "p1":
                p1count += 1
            elif i == "p2":
                p2count += 1
        if p1count + p2count == 3:
            if p1count >= 2:
                return "p1"
            elif p2count >= 2:
                return "p2"
            else: 
                #print(f"neither player won p1:{p1count}, p2:{p2count}")
                #print(self._caravan_status)
                #print(self._board)

                return ""
        else: 
            return ""
        
    # list of lists (card, caravan_index 1-6, caravan_card_index)
    def handleDirectionsSuits(self):
        print("bonus cards: ", self.bonus_cards)
        bonus_queens = []
        bonus_cards = self.bonus_cards
        for card in bonus_cards:
            if card[0] == 12:
                if len(card) < 4:
                    if card[1] > 2:
                        card[1] -= 3
                        card.append("p2")
                    else:
                        card.append("p1")
                bonus_queens.append(card) # 4th col = player

        for card in bonus_queens:
            if card[3] == "p1":
                if (card[2] == len(self._board.getCaravan1()[card[1]])-1) or (card[2] == len(self._board.getCaravan1()[card[1]])-2):
                    return
            elif card[3] == "p2":
                if (card[2] == len(self._board.getCaravan2()[card[1]])-1) or (card[2] == len(self._board.getCaravan2()[card[1]])-2):
                    return
                
        print("bonus queens: ", bonus_queens)

        # PLAYER 1
        number_cards1 = self._board.getCaravan1()  

        for i, caravan in enumerate(number_cards1):
            if len(number_cards1[i]) >= 2:
                if caravan[-1].value() > caravan[-2].value():
                    self._caravans1_direction[i] = ["ASC", caravan[-1].value()]
                elif caravan[-1].value() < caravan[-2].value():
                    self._caravans1_direction[i] = ["DESC", caravan[-1].value()]

        # SUITS
        for i, caravan in enumerate(self._board.getCaravan1()):
            if len(caravan) > 0:
                self._caravans1_suit[i] = self._board.getCaravan1()[i][-1].getSuit()
                    
        # PLAYER 2
        number_cards2 = self._board.getCaravan2()
 
        for i, caravan in enumerate(number_cards2):
            if len(number_cards2[i]) >= 2:
                if caravan[-1].value() > caravan[-2].value():
                    self._caravans2_direction[i] = ["ASC", caravan[-1].value()]
                elif caravan[-1].value() < caravan[-2].value():
                    self._caravans2_direction[i] = ["DESC", caravan[-1].value()]

        # SUITS
        for i, caravan in enumerate(self._board.getCaravan2()):
            if len(caravan) > 0:
                self._caravans2_suit[i] = self._board.getCaravan2()[i][-1].getSuit()

        #print(f"Directions: {self._caravans1_direction, self._caravans2_direction}, Suits: {self._caravans1_suit, self._caravans2_suit}")   
        
        
    def to_dict(self):
        # Return a simplified version of the game state as a dictionary
        return {
            'caravan_status': self._caravan_status,
            'hand1': self._hand1.to_dict(),
            'hand2': self._hand2.to_dict(),
            'board': self._board.toDict(),
            'discard_pile1': [card.to_dict() for card in self._discard_pile1],
            'discard_pile2': [card.to_dict() for card in self._discard_pile2],
            # 'bonus_cards': {item[0]: item[1:] for item in self.bonus_cards}
            'bonus_cards': self.bonus_cards,
            'player1' : self.player1,
            'player2' : self.player2,
            'caravan_values1' : self.caravan_values1,
            'caravan_values2' : self.caravan_values2,
            'game_id' : self.game_id,
            'waiting_for_player' : self.waiting_for_player,
            'gametype' : self.gametype,
            'current_turn' : self.getTurn(),
            'win_status' : self.win_status
        }
                
    
    def __str__(self):
        return str(self._board) + "\n" + str(self._hand1) + str(self._hand2)





if __name__ == "__main__":
    mygame = Game()
    #print(mygame)
    mygame.startGame()
    #print(mygame)

    

    mygame.placeCard("1", 1, 1)
    mygame.placeCard("1", 2, 1)
    mygame.placeCard("1", 3, 1)
    mygame.placeCard("1", 4, 1)

    mygame.placeCard("2", 1, 1)
    mygame.placeCard("2", 2, 1)
    mygame.placeCard("2", 3, 1)
    mygame.placeCard("2", 4, 1)

    #print(mygame.getValues())


    #print(mygame)
    
    #print(mygame.checkForWin())