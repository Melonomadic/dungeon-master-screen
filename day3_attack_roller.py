import random


def roll_attack(bonus):
    roll = random.randint(1,20)
    attack_roll = roll + bonus
    return attack_roll
bonus = int (input("Enter your attack bonus: "))
total_attack = roll_attack(bonus)
print("Your total attack roll is:", total_attack)