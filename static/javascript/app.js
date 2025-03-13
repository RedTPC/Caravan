document.addEventListener('DOMContentLoaded', function () {
    const socket = io();
    let selectedCard = null;

    socket.on("redirect", function (data) {
        window.location.href = data.url;  // Redirects to Flask route
    });

    // Start & Join Game
    document.getElementById("createGameButton").addEventListener("click", () => {
        console.log("Create game button clicked");
        socket.emit("create_game");
    });

        // Start & Join Game
    document.getElementById("createAIGameButton").addEventListener("click", () => {
        console.log("Create AI game button clicked");
        socket.emit("create_game_ai");
    });

    document.getElementById("createMultiplayerButton").addEventListener("click", () => {
        console.log("Create multiplayer game button clicked");
        socket.emit("create_multiplayer_game");
    });

    document.getElementById("joinGameButton").addEventListener("click", () => {
        const gameId = document.getElementById("gameIdInput").value.trim();
        if (gameId) {
            console.log("Join game button clicked with ID:", gameId);
            socket.emit("join_multiplayer_game", {game_id: gameId});
        }
    });

    function sleep(milliseconds) {
        var start = new Date().getTime();
        for (var i = 0; i < 1e7; i++) {
          if ((new Date().getTime() - start) > milliseconds){
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
        updateHands(data.hand1.hand, "hand1");
        updateHands(data.hand2.hand, "hand2");

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
        }   else {console.log("not ai move")}
    });

    function updateHands(handData, handClass) {
        const handElement = document.querySelector(`.${handClass}`);
        // Keep the heading
        handElement.innerHTML = `<h2>${handClass.charAt(0).toUpperCase() + handClass.slice(1)}</h2>`;

        handData.forEach((card, index) => {
            const cardElement = document.createElement("div");
            cardElement.classList.add("card");
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
            cardElement.classList.add("card", "small");
            cardElement.textContent = topCard.face + topCard.suit;
            discardZone1.appendChild(cardElement);
        }

        // Update player 2 discard pile
        const discardZone2 = document.querySelector('.discard-zone[data-player="2"]');
        discardZone2.innerHTML = "";
        if (discardPile2 && discardPile2.length > 0) {
            const topCard = discardPile2[discardPile2.length - 1];
            const cardElement = document.createElement("div");
            cardElement.classList.add("card", "small");
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
    
            const [cardValue, caravanIndex, positionIndex] = bonusCard;
            
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
    
});