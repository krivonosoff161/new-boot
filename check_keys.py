import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import sqlite3
import ccxt
from src.core.security_system_v3 import SecuritySystemV3

def main():
    print("Checking API keys...")
    
    # Get user data from database
    conn = sqlite3.connect('secure_users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, telegram_username, encrypted_api_key, encrypted_secret_key, 
               encrypted_passphrase, encryption_key, key_mode
        FROM secure_users 
        WHERE user_id = 462885677
    ''')
    
    user_data = cursor.fetchone()
    conn.close()
    
    if not user_data:
        print("User not found")
        return
    
    user_id, username, enc_api_key, enc_secret_key, enc_passphrase, enc_key, key_mode = user_data
    print(f"User: {username} (ID: {user_id})")
    print(f"Key mode: {key_mode}")
    
    # Decrypt keys
    try:
        security = SecuritySystemV3()
        credentials = security.decrypt_api_credentials(user_id)
        
        if not credentials:
            print("Failed to decrypt keys")
            return
        
        api_key, secret_key, passphrase = credentials
        print(f"API key: {api_key[:10]}...{api_key[-10:]}")
        print(f"Secret: {secret_key[:10]}...{secret_key[-10:]}")
        print(f"Passphrase: {passphrase}")
        
    except Exception as e:
        print(f"Decryption error: {e}")
        return
    
    # Test exchange connection
    try:
        exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': secret_key,
            'password': passphrase,
            'sandbox': key_mode == 'sandbox',
            'enableRateLimit': True,
        })
        
        print(f"Exchange: OKX")
        print(f"Mode: {'Sandbox' if key_mode == 'sandbox' else 'Live'}")
        
        print("Testing connection...")
        balance = exchange.fetch_balance()
        
        print("Connection successful!")
        print(f"Total balance: {balance.get('total', {})}")
        print(f"Free balance: {balance.get('free', {})}")
        print(f"Used balance: {balance.get('used', {})}")
        
        # Show main currencies
        print("Main currencies:")
        for currency in ['USDT', 'BTC', 'ETH', 'USD']:
            if currency in balance['total'] and balance['total'][currency] > 0:
                total = balance['total'][currency]
                free = balance['free'][currency]
                used = balance['used'][currency]
                print(f"  {currency}: {total} (free: {free}, used: {used})")
        
    except Exception as e:
        print(f"Exchange connection error: {e}")
        print(f"Error type: {type(e).__name__}")
        
        if "Invalid OK-ACCESS-KEY" in str(e):
            print("Possible causes:")
            print("- Invalid API key")
            print("- API key inactive")
            print("- Wrong mode (sandbox/live)")
        elif "Invalid OK-ACCESS-SIGN" in str(e):
            print("Possible causes:")
            print("- Invalid Secret key")
            print("- Invalid Passphrase")
        elif "Invalid OK-ACCESS-TIMESTAMP" in str(e):
            print("Possible causes:")
            print("- Time synchronization issues")

if __name__ == "__main__":
    main()
