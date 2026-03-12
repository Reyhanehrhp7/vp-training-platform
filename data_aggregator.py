import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

class DataAggregator:
    """Aggregates session JSON files into a SQLite database."""
    
    def __init__(self, db_path: str = "vp_sessions.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize SQLite database with required tables."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Sessions table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                case_key TEXT NOT NULL,
                case_name TEXT NOT NULL,
                personality_key TEXT NOT NULL,
                session_start TIMESTAMP NOT NULL,
                session_end TIMESTAMP,
                total_turns INTEGER,
                json_file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Conversation turns table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS turns (
                turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                turn_number INTEGER NOT NULL,
                speaker TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        
        # Feedback table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                turn_number INTEGER,
                competency TEXT,
                level TEXT,
                feedback_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id: str) -> bool:
        """Add a new user to the database."""
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO users (user_id) VALUES (?)
            ''', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding user {user_id}: {e}")
            return False
    
    def import_session(self, json_file_path: str) -> bool:
        """Import a single session JSON file into the database."""
        try:
            with open(json_file_path, 'r') as f:
                session_data = json.load(f)
            
            user_id = session_data.get("user_id")
            metadata = session_data.get("session_metadata", {})
            transcript = session_data.get("transcript", [])
            
            # Add user if not exists
            self.add_user(user_id)
            
            # Insert session
            self.cursor.execute('''
                INSERT INTO sessions 
                (user_id, case_key, case_name, personality_key, session_start, session_end, total_turns, json_file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                metadata.get("case"),
                metadata.get("case_name"),
                metadata.get("personality"),
                metadata.get("session_start"),
                metadata.get("session_end"),
                metadata.get("total_turns"),
                str(json_file_path)
            ))
            
            session_id = self.cursor.lastrowid
            
            # Insert turns
            for turn in transcript:
                self.cursor.execute('''
                    INSERT INTO turns (session_id, turn_number, speaker, message)
                    VALUES (?, ?, ?, ?)
                ''', (
                    session_id,
                    turn.get("turn"),
                    turn.get("speaker"),
                    turn.get("message")
                ))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error importing session from {json_file_path}: {e}")
            return False
    
    def import_all_sessions(self, data_dir: str = "data") -> Dict[str, int]:
        """Import all session JSON files from the data directory."""
        data_path = Path(data_dir)
        if not data_path.exists():
            print(f"Data directory {data_dir} not found.")
            return {"success": 0, "failed": 0, "total": 0}
        
        results = {"success": 0, "failed": 0, "total": 0}
        
        # Find all JSON files in user subdirectories
        json_files = list(data_path.glob("*/session_*.json"))
        results["total"] = len(json_files)
        
        for json_file in json_files:
            if self.import_session(str(json_file)):
                results["success"] += 1
            else:
                results["failed"] += 1
        
        return results
    
    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary statistics for a specific user."""
        try:
            self.cursor.execute('''
                SELECT 
                    COUNT(DISTINCT sessions.session_id) as total_sessions,
                    COUNT(DISTINCT sessions.case_key) as unique_cases,
                    COUNT(DISTINCT sessions.personality_key) as unique_personalities,
                    SUM(sessions.total_turns) as total_turns
                FROM sessions
                WHERE user_id = ?
            ''', (user_id,))
            
            result = self.cursor.fetchone()
            return {
                "user_id": user_id,
                "total_sessions": result[0] or 0,
                "unique_cases": result[1] or 0,
                "unique_personalities": result[2] or 0,
                "total_turns": result[3] or 0
            }
        except Exception as e:
            print(f"Error getting summary for user {user_id}: {e}")
            return {}
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all sessions from the database."""
        try:
            self.cursor.execute('''
                SELECT 
                    session_id, user_id, case_name, personality_key, 
                    session_start, session_end, total_turns
                FROM sessions
                ORDER BY session_start DESC
            ''')
            
            columns = [description[0] for description in self.cursor.description]
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        except Exception as e:
            print(f"Error getting all sessions: {e}")
            return []
    
    def get_sessions_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a specific user."""
        try:
            self.cursor.execute('''
                SELECT 
                    session_id, user_id, case_name, personality_key, 
                    session_start, session_end, total_turns
                FROM sessions
                WHERE user_id = ?
                ORDER BY session_start DESC
            ''', (user_id,))
            
            columns = [description[0] for description in self.cursor.description]
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        except Exception as e:
            print(f"Error getting sessions for user {user_id}: {e}")
            return []
    
    def get_case_statistics(self) -> List[Dict[str, Any]]:
        """Get statistics aggregated by case across all users."""
        try:
            self.cursor.execute('''
                SELECT 
                    case_name,
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(DISTINCT user_id) as unique_users,
                    AVG(total_turns) as avg_turns,
                    SUM(total_turns) as total_turns
                FROM sessions
                GROUP BY case_name
                ORDER BY total_sessions DESC
            ''')
            
            columns = [description[0] for description in self.cursor.description]
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        except Exception as e:
            print(f"Error getting case statistics: {e}")
            return []
    
    def get_personality_statistics(self) -> List[Dict[str, Any]]:
        """Get statistics aggregated by personality across all users."""
        try:
            self.cursor.execute('''
                SELECT 
                    personality_key,
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(DISTINCT user_id) as unique_users,
                    AVG(total_turns) as avg_turns,
                    SUM(total_turns) as total_turns
                FROM sessions
                GROUP BY personality_key
                ORDER BY total_sessions DESC
            ''')
            
            columns = [description[0] for description in self.cursor.description]
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        except Exception as e:
            print(f"Error getting personality statistics: {e}")
            return []
    
    def export_to_csv(self, output_dir: str = "exports"):
        """Export database tables to CSV files."""
        Path(output_dir).mkdir(exist_ok=True)
        import pandas as pd
        
        try:
            # Export sessions
            sessions_df = pd.read_sql_query("SELECT * FROM sessions", self.conn)
            sessions_df.to_csv(f"{output_dir}/sessions.csv", index=False)
            
            # Export turns
            turns_df = pd.read_sql_query("SELECT * FROM turns", self.conn)
            turns_df.to_csv(f"{output_dir}/turns.csv", index=False)
            
            # Export user summary
            users = self.cursor.execute("SELECT DISTINCT user_id FROM users").fetchall()
            summaries = [self.get_user_summary(user[0]) for user in users]
            summary_df = pd.DataFrame(summaries)
            summary_df.to_csv(f"{output_dir}/user_summary.csv", index=False)
            
            print(f"✅ Exported data to {output_dir}/")
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    # Example usage
    aggregator = DataAggregator("vp_sessions.db")
    
    print("📊 Importing sessions from data directory...")
    results = aggregator.import_all_sessions("data")
    print(f"✅ Imported {results['success']} sessions, {results['failed']} failed")
    
    print("\n📈 Case Statistics:")
    for stat in aggregator.get_case_statistics():
        print(f"  {stat['case_name']}: {stat['total_sessions']} sessions, {stat['unique_users']} users")
    
    print("\n📈 Personality Statistics:")
    for stat in aggregator.get_personality_statistics():
        print(f"  {stat['personality_key']}: {stat['total_sessions']} sessions, {stat['unique_users']} users")
    
    print("\n💾 Exporting to CSV...")
    aggregator.export_to_csv("exports")
    
    aggregator.close()
