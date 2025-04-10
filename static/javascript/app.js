const cardMap = {
    "A♣": "card_1.png",
    "A♦": "card_2.png",
    "A♥": "card_3.png",
    "A♠": "card_4.png",
    "2♣": "card_5.png",
    "2♦": "card_6.png",
    "2♥": "card_7.png",
    "2♠": "card_8.png",
    "3♣": "card_9.png",
    "3♦": "card_10.png",
    "3♥": "card_11.png",
    "3♠": "card_12.png",
    "4♣": "card_13.png",
    "4♦": "card_14.png",
    "4♥": "card_15.png",
    "4♠": "card_16.png",
    "5♣": "card_17.png",
    "5♦": "card_18.png",
    "5♥": "card_19.png",
    "5♠": "card_20.png",
    "6♣": "card_21.png",
    "6♦": "card_22.png",
    "6♥": "card_23.png",
    "6♠": "card_24.png",
    "7♣": "card_25.png",
    "7♦": "card_26.png",
    "7♥": "card_27.png",
    "7♠": "card_28.png",
    "8♣": "card_29.png",
    "8♦": "card_30.png",
    "8♥": "card_31.png",
    "8♠": "card_32.png",
    "9♣": "card_33.png",
    "9♦": "card_34.png",
    "9♥": "card_35.png",
    "9♠": "card_36.png",
    "10♣": "card_37.png",
    "10♦": "card_38.png",
    "10♥": "card_39.png",
    "10♠": "card_40.png",
    "J♣": "card_41.png",
    "J♦": "card_42.png",
    "J♥": "card_43.png",
    "J♠": "card_44.png",
    "Q♣": "card_45.png",
    "Q♦": "card_46.png",
    "Q♥": "card_47.png",
    "Q♠": "card_48.png",
    "K♣": "card_49.png",
    "K♦": "card_50.png",
    "K♥": "card_51.png",
    "K♠": "card_52.png"
  };

document.addEventListener('DOMContentLoaded', function () {
    const socket = io();
    let selectedCard = null;
    
    // Get the element with the 'user-info' id
    const userInfoElement = document.getElementById("user-info");

    // Access the current_user from the 'data-username' attribute
    const current_user = userInfoElement ? userInfoElement.dataset.username : null;

    console.log("Current User:", current_user);

    socket.on("redirect", function (data) {
        window.location.href = data.url;  // Redirects to Flask route
    });

    if (window.location.pathname.startsWith('/game/')) {
        // Extract game_id from URL
        const game_id = window.location.pathname.split('/').pop();
        
        // Store it globally so other functions can access it
        window.gameId = game_id;
        
        console.log("joining game room req game state, gameid = ", game_id)

        
        // Join the game room and request initial state
        socket.emit('join_game_room', {game_id: game_id});
        
        // Explicitly request game state after joining
        socket.emit('request_game_state', {game_id: game_id});

        // Add this to your waiting_room.html
        socket.on('game_joined', function(data) {
            if (data.game_id === game_id) {  // assuming you have currentGameId defined
                window.location.href = '/game/' + data.game_id;
            }
});
    }



    // Start & Join Game
    const create_game_button = document.getElementById("createGameButton")
    if (create_game_button) {
        create_game_button.addEventListener("click", () => {
            console.log("Create game button clicked");
            console.log("Socket status:", socket);
            socket.emit("create_game");
        });
    }

    // Start & Join Game
    const create_AI_game_button = document.getElementById("createAIGameButton")
    if (create_AI_game_button) {
        create_AI_game_button.addEventListener("click", () => {
            console.log("Create AI game button clicked");
            socket.emit("create_game_ai");
        });
    }

    const create_multiplayer_game_button = document.getElementById("createMultiplayerButton")
    if (create_multiplayer_game_button) {
        document.getElementById("createMultiplayerButton").addEventListener("click", () => {
            console.log("Create multiplayer game button clicked");
            socket.emit("create_multiplayer_game");
        });
    }

    const joinGameButton = document.getElementById("joinGameButton")
    if (joinGameButton) {
        joinGameButton.addEventListener("click", () => {
            const gameId = document.getElementById("gameIdInput").value.trim();
            if (gameId) {
                console.log("Join game button clicked with ID:", gameId);
                socket.emit("join_multiplayer_game", { game_id: gameId });
            }
        });
    }

    document.getElementById("useDeck").addEventListener("click", () => {
        console.log("Use deck button clicked");
        sendSelection()
    });

    const cancel_room_buttom = document.getElementById("cancel_room")
    if (cancel_room_buttom && gameId) {
        cancel_room_buttom.addEventListener("click", () => {
            console.log("Cancel room button clicked");
            socket.emit("cancel_room_buttom", { game_id: gameId });
        });
    }


    // DECK BUILDER STUFF


    document.addEventListener("click", (event) => {
        if (event.target && event.target.id === "saveDeckButton") {
            console.log("Save Deck Button Clicked");

            let selectedCards = [];
            document.querySelectorAll(".deck-card-slot.filled").forEach(slot => {
                selectedCards.push(slot.dataset.card);
            });

            if (selectedCards.length > 29) {

                console.log("Selected Cards:", selectedCards);

                socket.emit("save_deck", { selectedCards: selectedCards });
            } else {
                console.log("deck not big enough")
            }
        }
    });

    attachDeckOptionCardListeners();
    attachDeckSlotCardListeners();

    ///////////////////////////

    // deck selector

    requestDropdownOptions();



    function sleep(milliseconds) {
        var start = new Date().getTime();
        for (var i = 0; i < 1e7; i++) {
            if ((new Date().getTime() - start) > milliseconds) {
                break;
            }
        }
    }


    // Listen for board updates
    socket.on("game_update", (data) => {
        console.log("Game state updated", data);


        // Get the game_id from the URL
        const urlParams = new URLSearchParams(window.location.search);
        const gameId = urlParams.get('game_id');
        console.log("Game ID:", gameId);

        if (gameId != null) {
            // Access game state and update UI
            const player1 = data.player1;
            const player2 = data.player2;
            document.getElementById("player1").textContent = player1;
            document.getElementById("player2").textContent = player2 || "Waiting for Player 2";

        }

        console.log("game id: ", data.game_id)
        let game_id = data.game_id


        // Show the game container
        document.getElementById("gameContainer").style.display = "block";

        // Update hands
        console.log("")
        console.log(current_user)
        console.log(data.player1, data.player2)
        console.log("")


        console.log(data)
        
        if (current_user === data.player1) {
            updateHands(data.hand1.hand, "hand1", false); // hide=false
            updateHands(data.hand2.hand, "hand2", true); // hide = true
        } else if (current_user === data.player2) {
            updateHands(data.hand1.hand, "hand1", true); // hide=true
            updateHands(data.hand2.hand, "hand2", false); // hide = false
        } else {
            updateHands(data.hand1.hand, "hand1", false); // hide=false
            updateHands(data.hand2.hand, "hand2", false); // hide = false       
        }


        // highlight turn hand

        highlightCurrentTurn(data.current_turn)

        // Update board
        updateBoard(data.board, game_id);

        // update discard piles
        updateDiscardPiles(data.discard_pile1, data.discard_pile2, game_id);

        // update bonus cards
        updateBonusCards(data.bonus_cards, game_id);


        // Attach event listeners
        attachCardListeners(game_id);
        attachCaravanListeners(game_id);
        attachCaravanCardListeners(game_id);
        attachDiscardListeners(game_id);

        addImages();


        // Update caravan status if applicable
        updateCaravanStatus(data.caravan_status, game_id);

        // Update caravan values
        // if (data.caravan_values2 != null) {
        //     mergedValues = [...data.caravan_values1, ...data.caravan_values2];
        // }   else {
        //     mergedValues = data.caravan_values1
        // }
        mergedValues = [...data.caravan_values1, ...data.caravan_values2];
        console.log("Merged caravan values:", mergedValues);

        updateCaravanValues(mergedValues);

        // Update winner message if present
        if (data.win_status) {
            document.getElementById("winnerMessage").textContent = data.win_status;
            document.getElementById("winnerMessage").style.display = "block";
        } else {
            document.getElementById("winnerMessage").style.display = "none";
        }

        // IF IT IS A GAME VS AI 
        if (data.gametype === "AI" && data.current_turn === "2") {
            setTimeout(() => {
                console.log("AI's turn - making move");
                socket.emit("make_ai_move", game_id);
            }, 1000);

            console.log("making ai move")
            socket.emit("make_ai_move", game_id);
        } else { console.log("not ai move") }

    });

    function updateHands(handData, handClass, hide) {
        console.log("update hands called")
        const handElement = document.querySelector(`.${handClass}`);
        // Keep the heading
        handElement.innerHTML = "";

        handData.forEach((card, index) => {
            const cardElement = document.createElement("div");
            cardElement.classList.add("card");
            if (hide === true) {
                console.log("hide=true")
                cardElement.classList.add("hidden")
            }
            cardElement.textContent = card.face + card.suit;
            cardElement.dataset.card = card.face + card.suit;
            cardElement.dataset.index = index;
            handElement.appendChild(cardElement);
        });
    }

    function updateBoard(boardData) {
        // Update player 1's caravans
        boardData.caravans1.forEach((caravan, index) => {
            const caravanElement = document.querySelector(`.caravans1 .caravan[data-index="${index}"]`);
            caravanElement.innerHTML = "";
            caravan.forEach((card, cardIndex) => {
                const cardElement = document.createElement("div");
                cardElement.classList.add("card", "small");
                cardElement.textContent = card;
                caravanElement.appendChild(cardElement);


                // Check for bonus card at this position
                // addBonusCard(boardData.bonus_cards, index, cardIndex, caravanElement);
            });
        });

        // Update player 2's caravans
        boardData.caravans2.forEach((caravan, index) => {
            const caravanElement = document.querySelector(`.caravans2 .caravan[data-index="${index + 3}"]`);
            caravanElement.innerHTML = "";
            caravan.forEach((card, cardIndex) => {  // Corrected the syntax here
                const cardElement = document.createElement("div");
                cardElement.classList.add("card", "small");
                cardElement.textContent = card;
                caravanElement.appendChild(cardElement);

                // Check for bonus card at this position
                // addBonusCard(boardData.bonus_cards, index + 3, cardIndex, caravanElement);
            });
        });
    }


    function updateCaravanStatus(statusArray) {
        if (!statusArray) return;

        statusArray.forEach((status, index) => {

            const isPlayer2 = index >= 3; // Identify if it's player 2's caravan
            const adjustedIndex = isPlayer2 ? index - 3 : index; // Adjust index for player 2's caravans

            const caravan1 = document.querySelector(`.caravans1 .caravan[data-index="${adjustedIndex}"]`);
            const caravan2 = document.querySelector(`.caravans2 .caravan[data-index="${adjustedIndex + 3}"]`);

            // Reset classes
            caravan1.classList.remove("won", "lost");
            caravan2.classList.remove("won", "lost");

            if (status === "p1") {
                caravan1.classList.add("won");
                caravan2.classList.add("lost");
            } else if (status === "p2") {
                caravan1.classList.add("lost");
                caravan2.classList.add("won");
            }
        });
    }

    function attachCardListeners() {
        document.querySelectorAll(".hand1 .card, .hand2 .card").forEach(card => {
            card.addEventListener("click", function () {
                // Remove selected class from all cards
                document.querySelectorAll(".card").forEach(c => c.classList.remove("selected"));

                // Add selected class to this card
                this.classList.add("selected");

                // Get the hand index
                const inHand1 = this.closest(".hand1") !== null;
                const localIndex = parseInt(this.dataset.index);

                // Calculate the actual hand index (for server)
                selectedCard = inHand1 ? localIndex : localIndex + 8;

                console.log(`Selected card at index: ${selectedCard}`);
            });
        });
    }

    function attachCaravanCardListeners(game_id) {
        document.querySelectorAll('.caravan .card').forEach(card => {
            card.addEventListener('click', function () { // Use function() to keep `this` context
                console.log("Card clicked:", card.textContent);

                // Find the caravan element (parent of the clicked card)
                const caravanElement = card.closest('.caravan');
                const caravanIndex = parseInt(caravanElement.dataset.index);

                // Adjust caravanIndex for player 2's caravans (index >= 3)
                const isPlayer2 = caravanIndex >= 3;
                const adjustedIndex = isPlayer2 ? caravanIndex - 3 : caravanIndex;

                // Find the index of the clicked card within the caravan
                const caravanCards = Array.from(caravanElement.querySelectorAll('.card')); // Get all cards in the caravan
                const caravanCardIndex = caravanCards.indexOf(card); // Find the clicked card's index

                console.log(`Placing card from hand index ${selectedCard} to caravan ${adjustedIndex}, card slot ${caravanCardIndex}`);

                socket.emit("place_side_card", {
                    hand_index: selectedCard,
                    caravan_index: caravanIndex,
                    caravan_card_index: caravanCardIndex,
                    game_id: game_id
                });

                // Reset selection
                selectedCard = null;
                document.querySelectorAll(".card").forEach(c => c.classList.remove("selected"));
            });
        });
    }



    function attachCaravanListeners(game_id) {
        document.querySelectorAll(".caravan").forEach(slot => {
            slot.addEventListener("click", function () {
                if (selectedCard !== null) {
                    const caravanIndex = parseInt(this.dataset.index) % 3;

                    console.log(`Placing card from hand index ${selectedCard} to caravan ${caravanIndex}`);

                    const isPlayer2 = caravanIndex >= 3;
                    const adjustedIndex = isPlayer2 ? caravanIndex - 3 : caravanIndex;

                    socket.emit("place_card", {
                        hand_index: selectedCard,
                        caravan_index: adjustedIndex,
                        game_id: game_id
                    });

                    // Reset selection
                    selectedCard = null;
                    document.querySelectorAll(".card").forEach(c => c.classList.remove("selected"));
                }
            });
        });
    }

    function updateDiscardPiles(discardPile1, discardPile2) {
        // Update player 1 discard pile
        const discardZone1 = document.querySelector('.discard-zone[data-player="1"]');
        discardZone1.innerHTML = "";
        if (discardPile1 && discardPile1.length > 0) {
            const topCard = discardPile1[discardPile1.length - 1];
            const cardElement = document.createElement("div");
            cardElement.classList.add("card");
            cardElement.textContent = topCard.face + topCard.suit;
            discardZone1.appendChild(cardElement);
        }

        // Update player 2 discard pile
        const discardZone2 = document.querySelector('.discard-zone[data-player="2"]');
        discardZone2.innerHTML = "";
        if (discardPile2 && discardPile2.length > 0) {
            const topCard = discardPile2[discardPile2.length - 1];
            const cardElement = document.createElement("div");
            cardElement.classList.add("card");
            cardElement.textContent = topCard.face + topCard.suit;
            discardZone2.appendChild(cardElement);
        }
    }

    function updateCaravanValues(caravan_values) {

        if (!Array.isArray(caravan_values) || caravan_values.length < 6) {
            console.error("Invalid caravan values received:", caravan_values);
            return;
        }

        for (let i = 0; i < 3; i++) {
            const valueElement = document.querySelector(`.caravan-value[data-index="${i}"]`);
            if (valueElement) {
                valueElement.innerText = `Value: ${caravan_values[i]}`;
                valueElement.classList.toggle('winning-range', caravan_values[i] >= 21 && caravan_values[i] <= 26);
            }
        }

        for (let i = 3; i < 6; i++) {
            const valueElement = document.querySelector(`.caravan-value[data-index="${i}"]`);
            if (valueElement) {
                valueElement.innerText = `Value: ${caravan_values[i]}`;
                valueElement.classList.toggle('winning-range', caravan_values[i] >= 21 && caravan_values[i] <= 26);
            }
        }
    }


    function attachDiscardListeners(game_id) {
        document.querySelectorAll('.discard-zone').forEach(zone => {
            zone.addEventListener('click', function () {
                if (selectedCard !== null) {
                    const player = this.dataset.player;
                    const inHand1 = selectedCard < 8;

                    // Only allow discarding from the player's own hand
                    if ((player === "1" && inHand1) || (player === "2" && !inHand1)) {
                        console.log(`Discarding card from hand index ${selectedCard}`);

                        socket.emit("discard_card", {
                            hand_index: selectedCard,
                            game_id: game_id
                        });

                        // Reset selection
                        selectedCard = null;
                        document.querySelectorAll(".card").forEach(c => c.classList.remove("selected"));
                    }
                }
            });
        });
    }

    // function addBonusCard(bonusCards, caravanIndex, caravanCardIndex, caravanElement) {

    //     if (!Array.isArray(bonusCards)) {
    //         console.error("Bonus cards are not in the expected format:", bonusCards);
    //         return;
    //     }

    //     bonusCards.forEach(([bonusCard, bCaravanIndex, bCardIndex]) => {
    //         if (bCaravanIndex - 1 === caravanIndex && bCardIndex === caravanCardIndex) {
    //             const bonusCardElement = document.createElement("div");
    //             bonusCardElement.classList.add("card", "bonus-card");
    //             bonusCardElement.textContent = bonusCard;
    //             bonusCardElement.style.pointerEvents = "none"; // Make non-interactable

    //             // Append next to the main card
    //             caravanElement.appendChild(bonusCardElement);
    //         }
    //     });
    // }

    function updateBonusCards(bonusCards) {
        // First, clear all existing bonus cards
        document.querySelectorAll('.bonus-card').forEach(card => card.remove());

        // If bonusCards is null or not an array, exit
        if (!bonusCards || !Array.isArray(bonusCards)) {
            console.warn("No bonus cards or invalid format:", bonusCards);
            return;
        }

        // Loop through each bonus card data array
        bonusCards.forEach((bonusCard) => {
            // Check if the bonus card is in the expected array format [value, caravan_index, position_index]
            if (!Array.isArray(bonusCard) || bonusCard.length < 3) {
                console.warn("Invalid bonus card data:", bonusCard);
                return;
            }

            let [cardValue, caravanIndex, positionIndex] = bonusCard;

            if (cardValue === 12) {
                cardValue = "Q"
            } else if (cardValue === 13) {
                cardValue = "K"
            }

            // Determine which caravan element to target
            const caravanElement = document.querySelector(`.caravan[data-index="${caravanIndex}"]`);
            if (!caravanElement) {
                console.error(`Caravan element not found for index: ${caravanIndex}`);
                return;
            }

            // Get all regular cards in this caravan
            const cardElements = caravanElement.querySelectorAll(".card:not(.bonus-card)");

            // Find the target card
            if (positionIndex < cardElements.length) {
                const targetCard = cardElements[positionIndex];

                // Create a container for the card and its bonus if it doesn't exist
                let cardContainer = targetCard.parentElement;
                if (!cardContainer.classList.contains('card-container')) {
                    // Create a new container
                    cardContainer = document.createElement('div');
                    cardContainer.classList.add('card-container');
                    // Replace the card with the container that contains the card
                    targetCard.parentNode.replaceChild(cardContainer, targetCard);
                    cardContainer.appendChild(targetCard);
                }

                // Create the bonus card element
                const bonusCardElement = document.createElement("div");
                bonusCardElement.classList.add("bonus-card", "small");
                bonusCardElement.textContent = cardValue;  // Use the card value from the array

                // Add the bonus card to the container
                cardContainer.appendChild(bonusCardElement);
            }
        });
    }

    function attachDeckOptionCardListeners() {
        document.querySelectorAll(".deck-card-option").forEach(card => {
            card.addEventListener("click", function () {
                // Set selectedCard to the value of the clicked card (from the data-card attribute)
                selectedCard = this.dataset.card;
                console.log(`Selected card: ${selectedCard}`);

                // Add visual feedback (highlight the selected card)
                document.querySelectorAll(".deck-card-option").forEach(c => c.classList.remove("selected"));
                this.classList.add("selected");
            });
        });
    }

    function attachDeckSlotCardListeners() {
        document.querySelectorAll(".deck-card-slot").forEach(slot => {
            slot.addEventListener("click", function () {
                // Only proceed if a card is selected
                if (selectedCard !== null) {
                    // Check if the slot is already filled
                    if (this.dataset.card) {
                        alert("This slot is already filled!");
                        return;
                    }

                    // Visually move the card into the slot
                    this.textContent = `${selectedCard}`;  // Set the card text in the slot
                    this.classList.add("filled");  // Add a "filled" class for styling
                    this.dataset.card = selectedCard;  // Store the card data in the slot's dataset
                    this.style.backgroundColor = "white";
                    this.style.color = "black";

                    // Update the visual state of the card options (you may want to reset the selected card)
                    selectedCard = null;

                    // Optionally, reset the "selected" class for deck cards
                    document.querySelectorAll(".deck-card-option").forEach(c => c.classList.remove("selected"));
                } else {
                    alert("Please select a card first!");
                }
            });
        });
    }

    function requestDropdownOptions() {
        // Request dropdown options when the page loads
        socket.emit("deck_request_options");

        console.log("req dropdown options called")

        // Receive options from the server
        socket.on("dropdown_options", function (options) {

            console.log(options)

            let dropdown = document.getElementById("deck-options");

            if (dropdown != null) {
                dropdown.innerHTML = ""
                // Clear existing options

                // ADD IN THE DEFAULT PARAM
                let opt = document.createElement("option");
                opt.value = "deck0";
                opt.textContent = "Default";
                dropdown.appendChild(opt);

                options.forEach(option => {
                    let opt = document.createElement("option");
                    opt.value = option;
                    opt.textContent = option;
                    dropdown.appendChild(opt);
                });
                if (options.length === 0) {
                    console.log("options empty");
                }
            };
        });
    }

    function sendSelection() {
        let selectedValue = document.getElementById("deck-options").value;
        console.log("Selected:", selectedValue);
        socket.emit("deck_dropdown_selection", selectedValue);
    }

    // Function to update the game UI

    function updateGameUI(gameData) {
        // Implement your UI update logic here
        // This will depend on your game's structure
    }

    // Example function to handle player actions
    function playCard(cardId, position) {
        socket.emit('player_action', {
            game_id: gameId,
            action: 'play_card',
            card_id: cardId,
            position: position
        });
    }

    function highlightCurrentTurn(turn) {
        // Reset the highlighted class for both hands
        const hand1 = document.querySelector(".hand1");
        const hand2 = document.querySelector(".hand2");
    
        // Remove the highlighted class from both hands
        hand1.classList.remove("highlighted_hand");
        hand2.classList.remove("highlighted_hand");
    
        // Add the highlighted class to the current hand based on the turn
        if (turn === "1") {
            hand1.classList.add("highlighted_hand");
        } else if (turn === "2") {
            hand2.classList.add("highlighted_hand");
        }
    }

    function addImages() {
        document.querySelectorAll('.card').forEach(card => {
            console.log("big cardrecognised")

            const cardCode = card.getAttribute('data-card');
            const img = cardMap[cardCode];
            if (img) {
              card.style.backgroundImage = `url('../static/images/cards/${img}')`;
              card.style.backgroundSize = "100% 100%";
              card.style.width = "105px";
              card.style.height = "150px";
              card.style.borderRadius = "8px";
              card.style.backgroundPosition = "center";

            }

          });

          document.querySelectorAll('.card.small').forEach(card => {
            console.log("small cardrecognised")
            const cardCode = card.textContent;
            const img = cardMap[cardCode];
            if (img) {
                
                card.style.backgroundImage = `url('../static/images/cards/${img}')`;
                card.style.backgroundSize = "cover";
                card.style.width = "52.5px";
                card.style.height = "75px";
                card.style.borderRadius = "8px";
            }

          });
    }
    

});