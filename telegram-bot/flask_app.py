from flask import Flask, render_template, jsonify, request
import sqlite3
import os
import requests

app = Flask(__name__)

BOT_TOKEN = "8373273491:AAHKUfwPB2OYTfgejrz8Pbpim-NepdD--EU"

def get_username_from_telegram(user_id):
    """Fetch username from Telegram API"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
        response = requests.post(url, json={"chat_id": user_id}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                user = data['result']
                if 'username' in user and user['username']:
                    return f"@{user['username']}"
                elif 'first_name' in user:
                    return user['first_name']
                else:
                    return f"User {user_id}"
        return f"User {user_id}"
    except:
        return f"User {user_id}"

def init_db():
    conn = sqlite3.connect('keys.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS keys
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  key_value TEXT UNIQUE NOT NULL,
                  taken BOOLEAN DEFAULT FALSE,
                  taken_by TEXT,
                  taken_by_username TEXT,
                  taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    initial_keys = [
        "URru0x61",
        "URru0x62",
        "URru0x63",
        "URru0x64",
        "URru0x65",
        "URru0x66",
        "URru0x67",
        "URru0x68",
        "URru0x69",
        "URru0x6A"
    ]
    
    for key in initial_keys:
        try:
            c.execute("INSERT OR IGNORE INTO keys (key_value) VALUES (?)", (key,))
        except:
            pass
    
    conn.commit()
    conn.close()
    print("Database initialized with keys")

def delete_db():
    try:
        os.remove('keys.db')
        return True
    except:
        return False

def get_all_keys():
    conn = sqlite3.connect('keys.db')
    c = conn.cursor()
    c.execute("SELECT key_value, taken, taken_by, taken_by_username, taken_at FROM keys ORDER BY id")
    keys = c.fetchall()
    conn.close()
    
    processed_keys = []
    for key in keys:
        key_value, taken, taken_by, taken_by_username, taken_at = key
        
        if taken_by and not taken_by_username:
            username = get_username_from_telegram(taken_by)
            conn = sqlite3.connect('keys.db')
            c = conn.cursor()
            c.execute("UPDATE keys SET taken_by_username = ? WHERE taken_by = ?", (username, taken_by))
            conn.commit()
            conn.close()
            processed_keys.append((key_value, taken, taken_by, username, taken_at))
        else:
            processed_keys.append(key)
    
    return processed_keys

def add_key(key_value):
    conn = sqlite3.connect('keys.db')
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO keys (key_value) VALUES (?)", (key_value,))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def remove_key(key_value):
    conn = sqlite3.connect('keys.db')
    c = conn.cursor()
    c.execute("DELETE FROM keys WHERE key_value = ?", (key_value,))
    conn.commit()
    conn.close()
    return True

def update_all_usernames():
    conn = sqlite3.connect('keys.db')
    c = conn.cursor()
    c.execute("SELECT taken_by FROM keys WHERE taken = TRUE AND taken_by_username IS NULL")
    user_ids = c.fetchall()
    
    updated_count = 0
    for user_id_tuple in user_ids:
        user_id = user_id_tuple[0]
        username = get_username_from_telegram(user_id)
        c.execute("UPDATE keys SET taken_by_username = ? WHERE taken_by = ?", (username, user_id))
        updated_count += 1
    
    conn.commit()
    conn.close()
    return updated_count

@app.route('/')
def index():
    keys = get_all_keys()
    total_keys = len(keys)
    taken_keys = len([k for k in keys if k[1]])
    available_keys = total_keys - taken_keys
    
    return render_template('index.html', 
                         keys=keys, 
                         total_keys=total_keys,
                         taken_keys=taken_keys,
                         available_keys=available_keys)

@app.route('/api/keys')
def api_keys():
    keys = get_all_keys()
    keys_list = []
    for key in keys:
        keys_list.append({
            'key': key[0],
            'taken': bool(key[1]),
            'taken_by': key[2] if key[2] else 'Not claimed',
            'taken_by_username': key[3] if key[3] else 'Not claimed',
            'taken_at': key[4] if key[4] else 'N/A'
        })
    return jsonify(keys_list)

@app.route('/delete-database', methods=['POST'])
def delete_database():
    if delete_db():
        init_db()
        return "Database deleted and reset. All keys have been restored."
    return "Error deleting database"

@app.route('/add-key', methods=['POST'])
def add_key_route():
    key_value = request.form.get('key')
    if key_value:
        if add_key(key_value):
            return f"Key {key_value} added successfully"
        else:
            return "Error adding key"
    return "Invalid data"

@app.route('/remove-key', methods=['POST'])
def remove_key_route():
    key_value = request.form.get('key')
    if key_value:
        remove_key(key_value)
        return f"Key {key_value} removed"
    return "Invalid data"

@app.route('/update-usernames', methods=['POST'])
def update_usernames_route():
    updated_count = update_all_usernames()
    return f"Updated {updated_count} usernames"

init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5555)
