projectname = input ("Project Name: ")
filename =""
for character in projectname:
    if character == " ":
        filename = filename + "_"
    else:
        filename = filename + character 
print ("Valid File Name", filename) 