def main():
    # 1. Initialize an empty list to hold our monsters
    encounter = []
    
    while True:
        # 2. Display the Menu
        print("\n--- DM Screen ---")
        print("1. Add Monster to Encounter")
        print("2. View Encounter List")
        print("3. Save Encounter to File")
        print("4. Exit")
        
        choice = input("Choose an option (1-4): ")
        
        if choice == "1":
            # All these lines should align vertically
            name = input("Enter Monster Name: ")
            hp = input("Enter Monster HP: ")
            ac = input("Enter Monster AC: ")
            new_monster = {"name": name, "hp": int(hp), "ac": int(ac)}
            encounter.append(new_monster)
            
            print(f"Added {name} with {hp} HP and {ac} AC!")

        elif choice == "2":
            # --- TODO: WRITE THE VIEW LOGIC HERE ---
            print("\n--- Current Encounter ---")
            # Loop through encounter list and print each monster nicely.
            for monster in encounter:
                print (f"Name: {monster['name']} | HP: {monster['hp']}  | AC: {monster['ac']} ")

        elif choice == "3":
            # --- TODO: WRITE THE SAVE LOGIC HERE ---
            # Open "encounter.txt" in write mode.
            # Loop through the list and write each monster to the file.
            with open("encounter.txt", "w") as file:
                for monster in encounter:
                    file.write(f"{monster['name']} - HP: {monster['hp']} - AC: {monster['ac']} \n")

        elif choice == "4":
            print("Exiting program. Goodbye!")
            break
            
        else:
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    main()