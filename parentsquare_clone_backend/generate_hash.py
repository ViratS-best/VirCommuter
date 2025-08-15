import bcrypt

password = 'test123'.encode('utf-8')
hashed = bcrypt.hashpw(password, bcrypt.gensalt())
print(hashed.decode('utf-8'))