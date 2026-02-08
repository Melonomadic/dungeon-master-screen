password = input ("Input Password: ")
has_number = False
pw_number = "123456789"
for char in password:
    if char in pw_number:
        has_number = True

if has_number == True:
    print ("Password Accepted")
else:
    print ("Error: Password must contain a number")               