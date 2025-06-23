# import sqlite3
# import os

# DATABASE_NAME = 'excuse_generator.db'

# def get_db_connection():
#     """Establishes and returns a database connection."""
#     conn = sqlite3.connect(DATABASE_NAME)
#     conn.row_factory = sqlite3.Row  # This allows accessing columns by name
#     return conn

# def init_db():
#     """Initializes the database schema if it doesn't exist."""
#     with get_db_connection() as conn:
#         cursor = conn.cursor()
#         # Table to store generated excuses and their parameters
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS excuses (
#                 id TEXT PRIMARY KEY,
#                 excuse_text TEXT NOT NULL,
#                 scenario TEXT NOT NULL,
#                 user_role TEXT,
#                 recipient TEXT,
#                 urgency TEXT,
#                 believability INTEGER,
#                 language TEXT,
#                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
#             )
#         ''')
#         # Table to store user feedback on excuse effectiveness
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS feedback (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 excuse_id TEXT NOT NULL,
#                 is_effective BOOLEAN NOT NULL,
#                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
#                 FOREIGN KEY (excuse_id) REFERENCES excuses (id)
#             )
#         ''')
#         conn.commit()

# if __name__ == '__main__':
#     # This block runs only when database.py is executed directly
#     # Useful for initial setup or rebuilding the database
#     if os.path.exists(DATABASE_NAME):
#         os.remove(DATABASE_NAME) # Remove existing db for a clean start
#         print(f"Removed existing database: {DATABASE_NAME}")
#     init_db()
#     print(f"Database '{DATABASE_NAME}' initialized successfully.")