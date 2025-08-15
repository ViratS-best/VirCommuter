import bcrypt

# The password you are trying to log in with
password_to_check = 'student_password123'.encode('utf-8')

# The password hash from your database
hashed_password_from_db = '$2b$12$34sYQp5pX25X6f2u11eW9uE9e9.b.p.w.b2u.n.D.q'.encode('utf-8')

# Check if the password matches the hash
if bcrypt.checkpw(password_to_check, hashed_password_from_db):
    print("Password matches!")
else:
    print("Password does NOT match.")