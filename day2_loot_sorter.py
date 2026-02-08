loot_list = ["Potion", "Sword", "Potion", "Shield", "Potion", "Gem"]
inventory = {}
for item in loot_list:
    if item in inventory:
        inventory[item] += 1
    else:
        inventory[item] = 1
print(inventory)