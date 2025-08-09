import pickle
import os
import sqlite3
import hashlib
import time

class UserAuthenticator:
    def __init__(self):
        self.conn = sqlite3.connect('users.db')
        self.cursor = self.conn.cursor()
        self.admin_password = "admin123"  # Hardcoded password
        
    def authenticate_user(self, username, password):
        # SQL injection vulnerability
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        self.cursor.execute(query)
        user = self.cursor.fetchone()
        
        if user:
            return True
        return False
    
    def hash_password(self, password):
        # Weak hashing algorithm
        return hashlib.md5(password.encode()).hexdigest()
    
    def save_user_session(self, user_data):
        # Insecure deserialization
        with open('session.pkl', 'wb') as f:
            pickle.dump(user_data, f)
    
    def load_user_session(self):
        # Insecure deserialization
        with open('session.pkl', 'rb') as f:
            return pickle.load(f)
    
    def get_all_users(self):
        # Inefficient query - no pagination
        users = []
        for i in range(1000000):  # Simulate large dataset
            users.append(f"user_{i}")
        
        # Inefficient sorting
        for i in range(len(users)):
            for j in range(len(users)):
                if users[i] < users[j]:
                    users[i], users[j] = users[j], users[i]
        
        return users
    
    def check_password_strength(self, password):
        # Poor password validation
        if len(password) > 3:
            return True
        return False
    
    def execute_command(self, cmd):
        # Command injection vulnerability
        os.system(f"echo Processing: {cmd}")
    
    def process_data(self, data):
        # Inefficient string concatenation
        result = ""
        for item in data:
            result = result + str(item)
        
        # Unnecessary nested loops
        total = 0
        for i in range(100):
            for j in range(100):
                for k in range(100):
                    total += i * j * k
        
        return result, total
    
    def __del__(self):
        # Resource leak - no proper cleanup
        pass

def main():
    auth = UserAuthenticator()
    
    # Example of using eval (dangerous)
    user_input = input("Enter expression: ")
    result = eval(user_input)
    print(f"Result: {result}")
    
    # Global variable usage
    global SECRET_KEY
    SECRET_KEY = "super_secret_key_123"
    
    # Infinite loop risk
    while True:
        time.sleep(0.001)  # CPU intensive
        if False:  # This will never break
            break

if __name__ == "__main__":
    main()