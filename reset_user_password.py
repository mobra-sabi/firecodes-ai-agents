#!/usr/bin/env python3
"""
🔑 Script pentru resetare parolă utilizator sau creare utilizator nou
Usage: python3 reset_user_password.py <email> <new_password>
       python3 reset_user_password.py <email> <new_password> --create
"""

import sys
import bcrypt
from pymongo import MongoClient
from datetime import datetime, timezone

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def reset_password(email: str, new_password: str, create_if_not_exists: bool = False):
    """Reset password for a user or create new user"""
    mongo = MongoClient("mongodb://localhost:27017")
    db = mongo["ai_agents_db"]
    
    # Find user
    user = db.users.find_one({"email": email})
    
    if not user:
        if create_if_not_exists:
            # Create new user
            print(f"📝 Creating new user: {email}")
            user_data = {
                "email": email,
                "password_hash": hash_password(new_password),
                "full_name": email.split("@")[0],
                "role": "user",
                "created_at": datetime.now(timezone.utc),
            }
            result = db.users.insert_one(user_data)
            print(f"✅ User created successfully!")
            print(f"   Email: {email}")
            print(f"   Password: {new_password}")
            print(f"   User ID: {result.inserted_id}")
            return True
        else:
            print(f"❌ User not found: {email}")
            print(f"   Use --create flag to create a new user")
            return False
    
    # Update password
    password_hash = hash_password(new_password)
    db.users.update_one(
        {"email": email},
        {"$set": {"password_hash": password_hash}}
    )
    
    print(f"✅ Password reset successfully!")
    print(f"   Email: {email}")
    print(f"   New Password: {new_password}")
    return True

def list_users():
    """List all users"""
    mongo = MongoClient("mongodb://localhost:27017")
    db = mongo["ai_agents_db"]
    
    users = list(db.users.find({}))
    print(f"\n👤 USERS IN DATABASE ({len(users)} total):\n")
    for user in users:
        print(f"  Email: {user.get('email')}")
        print(f"    Role: {user.get('role', 'user')}")
        print(f"    Created: {user.get('created_at', 'N/A')}")
        print()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("🔑 User Password Reset Tool")
        print("\nUsage:")
        print("  python3 reset_user_password.py <email> <new_password>")
        print("  python3 reset_user_password.py <email> <new_password> --create")
        print("  python3 reset_user_password.py --list")
        print("\nExamples:")
        print("  python3 reset_user_password.py admin@example.com admin123 --create")
        print("  python3 reset_user_password.py george.neculai@tehnica-antifoc.ro newpassword")
        sys.exit(0)
    
    if sys.argv[1] == "--list":
        list_users()
        sys.exit(0)
    
    if len(sys.argv) < 3:
        print("❌ Error: Email and password required")
        print("Usage: python3 reset_user_password.py <email> <new_password> [--create]")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    create = "--create" in sys.argv
    
    reset_password(email, password, create)

