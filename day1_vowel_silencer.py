sentence = input ("Enter a spell incantation: ")
vowels = "aeiouAEIOU"
silenced_sentence = ""
for letter in sentence:
    if letter not in vowels:
        silenced_sentence = silenced_sentence + letter
            

print ("Silenced version:", silenced_sentence) 