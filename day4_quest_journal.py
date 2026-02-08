journal_entry = input("Enter your journal entry: ")
with open("journal.txt", "a") as file:
    file.write(journal_entry + "\n")
with open("journal.txt", "r") as file:
    journal_history = file.read()
    print("---Journal History---" + "\n" + journal_history)
    