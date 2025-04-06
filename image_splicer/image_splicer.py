from PIL import Image

# Load the image
img = Image.open("fallout cards.jpg")

# Set number of rows and columns (e.g., 4 rows x 13 columns)
rows = 6
cols = 10

# Get the width and height of each card
card_width = img.width // cols
card_height = img.height // rows

# Slice and save each card
for row in range(rows):
    for col in range(cols):
        left = col * card_width
        top = row * card_height
        right = left + card_width
        bottom = top + card_height
        card = img.crop((left, top, right, bottom))
        card.save(f"card_{row * cols + col + 1}.png")
