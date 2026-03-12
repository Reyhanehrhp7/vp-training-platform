# Virtual Patient System - Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Start the Training App
```bash
streamlit run app.py
```
Opens at `http://localhost:8501`

### Step 2: Enter Your Student ID
- In the left sidebar, find "👤 User Information"
- Enter your Student/User ID (e.g., `S123456` or `student@univ.edu`)
- Select a case and personality mode
- Click "🚀 Start"

### Step 3: Complete Training Session
- Interact with the Virtual Patient
- Receive feedback after each turn
- Click "⏹️ End" to finish
- **Session automatically saves** to `data/[your_id]/session_*.json`

---

## 📊 View Your Data

### Option A: Individual Session Review
Sessions are saved as JSON files in:
```
data/
├── S123456/
│   └── session_migraine_neutral_20240115_143022.json
```

### Option B: Dashboard View
```bash
streamlit run data_dashboard.py
```
- **📈 Overview**: Total sessions, users, turns
- **👥 Users**: Filter by user and see their stats
- **📋 All Sessions**: Browse and search all sessions
- **📊 Analytics**: Case/personality stats and export

---

## 💾 Aggregate Data for Analysis

### Combine All Sessions into Database
```bash
python data_aggregator.py
```

This creates:
- `vp_sessions.db` - SQLite database with all data
- `exports/` folder with CSV files:
  - `sessions.csv` - All session metadata
  - `turns.csv` - All conversation turns
  - `user_summary.csv` - Per-user statistics

---

## 📁 File Locations

| File | Purpose |
|------|---------|
| `app.py` | Main training app |
| `data_dashboard.py` | Analytics dashboard |
| `data_aggregator.py` | Database management |
| `data/[user_id]/` | Session storage |
| `vp_sessions.db` | SQLite database |
| `exports/` | CSV exports |

---

## ⚙️ Configuration

### Change OpenAI API Key
Edit `app.py` line 15:
```python
API_KEY = "your-key-here"
```

---

## 🎯 Workflow for Instructors

1. **Distribute system** to students with instructions to run `streamlit run app.py`
2. **Students enter their ID** when prompted
3. **Students complete training sessions** (auto-saves)
4. **You aggregate data**: `python data_aggregator.py`
5. **Review in dashboard**: `streamlit run data_dashboard.py`
6. **Export for analysis**: Click "Export to CSV" in Analytics tab

---

## 📋 What Gets Saved

Each session automatically saves:
- ✅ User ID
- ✅ Case details (patient history, presenting complaint)
- ✅ Personality mode
- ✅ Full conversation transcript
- ✅ Session timestamp
- ✅ Number of turns

---

## 💡 Tips

- **Save your User ID** - Use same ID for all sessions to track progress
- **Try different cases** - Practice with all 4 cases (migraine, TIA, Parkinson's, astrocytoma)
- **Try different personalities** - Each personality changes patient behavior
- **Review feedback** - Read real-time feedback to improve skills
- **Check dashboard** - See your progress over time in the analytics dashboard

---

## ❓ Troubleshooting

**Issue: "Please enter your User ID first"**
- Solution: Type your Student/User ID in sidebar and press Enter

**Issue: Session not saving**
- Solution: Check that `data/` folder exists or is writable
- The app creates it automatically if missing

**Issue: Dashboard shows no data**
- Solution: Run `python data_aggregator.py` to import JSON files into database

**Issue: "OpenAI API error"**
- Solution: Check that API_KEY in app.py is valid
- Make sure you have OpenAI credits available

---

## 📚 Full Documentation

See `README_MULTIUSER.md` for detailed technical documentation.

---

**Questions?** Check the README or contact your instructor.
