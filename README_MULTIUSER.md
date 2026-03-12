# Virtual Patient Training System - Multi-User Guide

## Overview

The Virtual Patient (VP) system now supports multi-user data collection and analysis. Users can train on clinical communication skills, and all sessions are automatically saved and aggregated into a central database for analysis.

## System Components

### 1. **Main Application** (`app.py`)
- Streamlit web interface for VP training
- Two interaction modes in one interface:
  - **VP (AI Patient)**: doctor/user chats with AI patient
  - **SP (Human Standardized Patient)**: doctor/user chats with a human SP patient via shared session ID
- User ID input in sidebar (required before starting session)
- 4 clinical cases with 4 personality modes
- Real-time feedback based on 6 clinical competencies
- **Auto-save on session end**: Sessions automatically save to `data/[user_id]/` folder

### 2. **Data Aggregator** (`data_aggregator.py`)
- SQLite database management
- Imports JSON session files into structured database
- Generates statistics and reports
- Tables:
  - `users`: User IDs and creation timestamps
  - `sessions`: Session metadata (case, personality, turns, etc.)
  - `turns`: Individual conversation turns
  - `feedback`: Turn-level and session-level feedback (future expansion)

### 3. **Data Dashboard** (`data_dashboard.py`)
- Streamlit analytics dashboard
- View all collected sessions
- Filter by user, case, or personality
- User-specific statistics
- Case and personality performance metrics
- Export data to CSV

## Workflow

### For SP (Human) Sessions

1. **Doctor/User side**
  - Open `streamlit run app.py`
  - Select **SP (Human Standardized Patient)**
  - Set role to **Doctor (User)**
  - Enter User ID
  - Optional: enter a session ID, or leave blank for auto-generated ID
  - Select case and click Start
  - Session appears in SP waiting list

2. **SP patient side**
  - Open the same app (same server URL)
  - Select **SP (Human Standardized Patient)**
  - Set role to **SP Patient (Human)**
  - Enter SP Patient ID
  - Choose a session from **Available doctor sessions**
  - Click **Join Selected Session**
  - Click Start

3. **Live chat behavior**
  - Doctor and SP patient exchange messages in the same chat timeline
  - Auto-refresh updates messages every few seconds (manual refresh also available)
  - Click **End** to save transcript and close the live session

### For VP (AI) Sessions

Use the existing VP flow (AI response + feedback generation), unchanged except for selecting **VP (AI Patient)** mode in the sidebar.

### For Users (Clinicians/Students)

1. **Start Training**
   - Go to `http://localhost:8501` (when running `streamlit run app.py`)
   - Enter your **Student/User ID** in the sidebar (e.g., `S123456` or `student@university.edu`)
   - Select a case and personality mode
   - Click "🚀 Start"

2. **During Session**
   - Conduct interview with virtual patient
   - Receive real-time feedback after each turn
   - Continue for multiple turns

3. **End Session**
   - Click "⏹️ End" button
   - Session automatically saves to: `data/[your_user_id]/session_[case]_[personality]_[timestamp].json`
   - You'll see confirmation message

### For Instructors/Researchers

1. **View Individual Sessions**
   - Use data_dashboard.py to browse all sessions
   - Filter by user to see their progress
   - View detailed transcripts and turn counts

2. **Aggregate Data**
   ```bash
   python data_aggregator.py
   ```
   - Scans `data/` directory for all JSON files
   - Imports them into `vp_sessions.db` SQLite database
   - Generates CSV exports in `exports/` folder

3. **Access Dashboard**
   ```bash
   streamlit run data_dashboard.py
   ```
   - View statistics across all users
   - See case and personality performance metrics
   - Export data for external analysis

## Data Structure

### Session JSON File
```
data/
├── S123456/
│   ├── session_migraine_neutral_20240115_143022.json
│   ├── session_tia_anxious_20240115_144530.json
│   └── session_parkinsons_demanding_20240115_150145.json
├── S789012/
│   └── session_astrocytoma_somatizing_20240115_152301.json
```

### Session JSON Content
```json
{
  "user_id": "S123456",
  "session_metadata": {
    "case": "migraine",
    "case_name": "Migraine with Aura",
    "personality": "neutral",
    "total_turns": 8,
    "session_start": "2024-01-15T14:30:22",
    "session_end": "2024-01-15T14:35:45"
  },
  "case_details": { ... },
  "personality_details": { ... },
  "transcript": [
    {
      "turn": 1,
      "speaker": "Clinician",
      "role": "user",
      "message": "Good morning, how can I help you today?"
    },
    {
      "turn": 2,
      "speaker": "Patient",
      "role": "assistant",
      "message": "I've been having terrible headaches..."
    }
  ]
}
```

### Database Schema
- **users**: user_id (PK), created_at
- **sessions**: session_id (PK), user_id (FK), case_key, case_name, personality_key, session_start, session_end, total_turns, json_file_path
- **turns**: turn_id (PK), session_id (FK), turn_number, speaker, message
- **feedback**: feedback_id (PK), session_id (FK), turn_number, competency, level, feedback_text

## Usage Examples

### Example 1: Import All Sessions
```python
from data_aggregator import DataAggregator

aggregator = DataAggregator("vp_sessions.db")
results = aggregator.import_all_sessions("data")
print(f"Imported {results['success']} sessions")
```

### Example 2: Get User Summary
```python
summary = aggregator.get_user_summary("S123456")
print(f"Sessions: {summary['total_sessions']}")
print(f"Cases tried: {summary['unique_cases']}")
print(f"Total interactions: {summary['total_turns']}")
```

### Example 3: Get Case Statistics
```python
stats = aggregator.get_case_statistics()
for case in stats:
    print(f"{case['case_name']}: {case['total_sessions']} sessions by {case['unique_users']} users")
```

### Example 4: Export Data
```python
aggregator.export_to_csv("exports")
# Creates: exports/sessions.csv, exports/turns.csv, exports/user_summary.csv
```

## Running the System

### 1. Train on Virtual Patient
```bash
streamlit run app.py
```
- Visit `http://localhost:8501`
- Enter User ID
- Start training session
- Click "End" when done (auto-saves)

### 2. View Dashboard
```bash
streamlit run data_dashboard.py
```
- In "📈 Overview" tab: See total sessions, users, turns
- In "👥 Users" tab: Select user to view their stats and sessions
- In "📋 All Sessions" tab: Browse all sessions with filters
- In "📊 Analytics" tab: View case/personality performance and export data

### 3. Aggregate Data (from command line)
```bash
python data_aggregator.py
```
- Imports all JSON files from `data/` directory
- Populates SQLite database
- Exports to CSV files in `exports/` directory

## API Reference

### VPConversationManager
```python
from vp_interaction import VPConversationManager

manager = VPConversationManager("migraine", "neutral", api_key)
response = manager.get_vp_response("Tell me about your headache")
history = manager.get_conversation_history()
manager.reset_conversation()
```

### FeedbackGenerator
```python
from vp_feedback import FeedbackGenerator

generator = FeedbackGenerator(api_key)
feedback = generator.generate_turn_feedback("your message", "patient response")
summary = generator.generate_session_summary_feedback(conversation_history)
```

### DataAggregator
```python
from data_aggregator import DataAggregator

agg = DataAggregator("vp_sessions.db")
agg.import_all_sessions("data")
agg.get_user_summary("user_id")
agg.get_all_sessions()
agg.get_case_statistics()
agg.get_personality_statistics()
agg.export_to_csv("exports")
```

## File Organization

```
VP creation/
├── app.py                    # Main training app
├── data_dashboard.py         # Analytics dashboard
├── data_aggregator.py        # Database management
├── vp_interaction.py         # Conversation engine
├── vp_feedback.py            # Feedback generator
├── vp_builder.py             # System prompt builder
├── vp_cases.py               # Clinical cases
├── vp_personalities.py       # Personality modes
├── json_reader.py            # JSON utilities
├── data/                     # Session storage (auto-created)
│   ├── S123456/
│   │   ├── session_*.json
│   └── S789012/
│       └── session_*.json
├── vp_sessions.db            # SQLite database (auto-created)
└── exports/                  # CSV exports (auto-created)
    ├── sessions.csv
    ├── turns.csv
    └── user_summary.csv
```

## Configuration

### API Key
Edit `app.py` line 15:
```python
API_KEY = "your-openai-api-key-here"
```

### Database Location
Edit `data_aggregator.py` call:
```python
aggregator = DataAggregator("path/to/database.db")
```

### Data Directory
Default: `data/` (in current working directory)
Change in `data_aggregator.py`:
```python
aggregator.import_all_sessions("path/to/data")
```

## Future Enhancements

- [ ] Authentication system for user management
- [ ] Performance trends and progress tracking
- [ ] Peer comparison analytics
- [ ] Feedback history per user
- [ ] Case-by-case performance breakdown
- [ ] Export to Excel with formatting
- [ ] Data visualization charts
- [ ] Email notifications for session completion
- [ ] Mobile app for session access
