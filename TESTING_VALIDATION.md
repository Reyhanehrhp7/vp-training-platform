# Testing & Validation Guide - Multi-User VP System

## ✅ Validation Checklist

Use this guide to verify the multi-user system is working correctly.

---

## 1. User ID Input System

### Test: Enter User ID
**Steps:**
1. Run: `streamlit run app.py`
2. Look at sidebar for "👤 User Information" section
3. Type a test ID like: `test_student_001`
4. Verify text appears in input field

**Expected Result:** ✅ User ID input visible and accepts text

**Common Issues:**
- ❌ Input field not showing: Restart streamlit
- ❌ Placeholder text not visible: Check browser zoom

---

## 2. User ID Validation

### Test: Start without User ID
**Steps:**
1. Don't enter User ID
2. Select a case (e.g., "Migraine")
3. Select a personality (e.g., "Neutral")
4. Click "🚀 Start"

**Expected Result:** ✅ Error message appears: "⚠️ Please enter your User ID first"

### Test: Start with User ID
**Steps:**
1. Enter User ID: `test_001`
2. Select case and personality
3. Click "🚀 Start"

**Expected Result:** ✅ Session starts, chat interface appears

---

## 3. Auto-Save with User Organization

### Test: Session Saves to User Folder
**Steps:**
1. Start a session with User ID: `test_student_002`
2. Type a greeting: "Hello, what brings you in today?"
3. Wait for patient response
4. Type 2-3 follow-up messages
5. Click "⏹️ End"

**Expected Result:** ✅ Success message shows: 
```
✅ Session saved to: data\test_student_002\session_migraine_neutral_YYYYMMDD_HHMMSS.json
```

### Test: Folder Structure Created
**Steps:**
1. Open file explorer
2. Navigate to VP creation folder
3. Check `data/` directory

**Expected Result:** ✅ Folder structure exists:
```
data/
└── test_student_002/
    └── session_migraine_neutral_20240115_143022.json
```

### Test: JSON Contains User ID
**Steps:**
1. Open the saved JSON file in a text editor
2. Search for "user_id"

**Expected Result:** ✅ JSON contains:
```json
{
  "user_id": "test_student_002",
  "session_metadata": { ... }
}
```

---

## 4. Multiple Sessions Same User

### Test: Save Sessions from Same User
**Steps:**
1. Session 1: User ID "test_003", Case "Migraine", Personality "Neutral"
   - Have 3 turns of conversation
   - Click "End"
   - Verify saves to: `data/test_003/session_migraine_neutral_*.json`

2. Session 2: Same user "test_003", Case "TIA", Personality "Anxious"
   - Have 3 turns of conversation
   - Click "End"
   - Verify saves to: `data/test_003/session_tia_anxious_*.json`

**Expected Result:** ✅ Both files in same user folder:
```
data/
└── test_003/
    ├── session_migraine_neutral_20240115_143022.json
    └── session_tia_anxious_20240115_150145.json
```

---

## 5. Data Aggregator

### Test: Import Sessions into Database
**Steps:**
1. Create 3 test sessions using app.py (different users and cases)
2. Run in terminal: `python data_aggregator.py`
3. Check output for success message

**Expected Result:** ✅ Output shows:
```
📊 Importing sessions from data directory...
✅ Imported 3 sessions, 0 failed
```

### Test: Database Created
**Steps:**
1. Check file explorer for `vp_sessions.db` in VP creation folder
2. File size should be > 8 KB

**Expected Result:** ✅ SQLite database file exists

### Test: CSV Exports Created
**Steps:**
1. After running aggregator, check `exports/` folder
2. Should contain 3 CSV files

**Expected Result:** ✅ Files exist:
```
exports/
├── sessions.csv
├── turns.csv
└── user_summary.csv
```

### Test: CSV Data Content
**Steps:**
1. Open `exports/sessions.csv` in spreadsheet program
2. Look for columns: user_id, case_key, case_name, personality_key, total_turns

**Expected Result:** ✅ CSV contains rows with all sessions

---

## 6. Data Dashboard

### Test: Dashboard Starts
**Steps:**
1. Run: `streamlit run data_dashboard.py`
2. Wait for app to load

**Expected Result:** ✅ Dashboard loads at `http://localhost:8501`

### Test: Overview Tab
**Steps:**
1. Click "📈 Overview" tab
2. Look for metrics and charts

**Expected Result:** ✅ Shows:
- Total Sessions (metric)
- Unique Users (metric)
- Total Turns (metric)
- Avg Turns/Session (metric)
- Case bar chart
- Personality bar chart

### Test: Users Tab
**Steps:**
1. Click "👥 Users" tab
2. Select a user from dropdown (should show test users created)
3. View their session list

**Expected Result:** ✅ Shows:
- User dropdown populated with created users
- User statistics (sessions, cases, personalities, turns)
- Table of sessions for selected user

### Test: All Sessions Tab
**Steps:**
1. Click "📋 All Sessions" tab
2. See full table of sessions

**Expected Result:** ✅ Shows:
- Table with columns: Start Time, User ID, Case, Personality, Turns
- Filter controls for Case, Personality, User ID

### Test: Session Details Viewer
**Steps:**
1. In "All Sessions" tab, select a session from dropdown
2. View conversation below

**Expected Result:** ✅ Shows:
- Session metadata (ID, case, personality, user)
- Full conversation with Clinician/Patient labels
- All turns from the session

### Test: Analytics Tab
**Steps:**
1. Click "📊 Analytics" tab
2. View statistics

**Expected Result:** ✅ Shows:
- Case performance table
- Personality performance table
- Export to CSV button

### Test: Export Button
**Steps:**
1. Click "Export to CSV" button in Analytics tab
2. Wait for success message
3. Check `exports/` folder

**Expected Result:** ✅ Sees message: "✅ Data exported to exports/ directory"
CSV files updated with latest data

---

## 7. Database Queries

### Test: User Summary Query
**Steps:**
```python
from data_aggregator import DataAggregator

agg = DataAggregator("vp_sessions.db")
summary = agg.get_user_summary("test_001")
print(summary)
```

**Expected Result:** ✅ Output shows:
```python
{
  'user_id': 'test_001',
  'total_sessions': 2,
  'unique_cases': 2,
  'unique_personalities': 1,
  'total_turns': 8
}
```

### Test: Get All Sessions
**Steps:**
```python
agg = DataAggregator("vp_sessions.db")
sessions = agg.get_all_sessions()
print(f"Total: {len(sessions)}")
for session in sessions[:2]:
    print(session)
```

**Expected Result:** ✅ Returns list of session dictionaries with user_id, case_name, etc.

### Test: Case Statistics
**Steps:**
```python
agg = DataAggregator("vp_sessions.db")
stats = agg.get_case_statistics()
for stat in stats:
    print(f"{stat['case_name']}: {stat['total_sessions']} sessions")
```

**Expected Result:** ✅ Shows statistics grouped by case

---

## 8. End-to-End Workflow

### Complete Test Scenario
**Goal:** Simulate real instructor workflow

**Steps:**

1. **Create test data**
   ```bash
   # User 1: Try 2 cases
   streamlit run app.py
   # Session 1: ID=student_001, case=migraine, personality=neutral
   # Do 5 turns, End
   # Session 2: ID=student_001, case=tia, personality=anxious
   # Do 4 turns, End
   
   # User 2: Try 1 case
   # Session 3: ID=student_002, case=parkinsons, personality=demanding
   # Do 3 turns, End
   ```

2. **Verify files saved**
   ```
   data/
   ├── student_001/
   │   ├── session_migraine_neutral_*.json
   │   └── session_tia_anxious_*.json
   └── student_002/
       └── session_parkinsons_demanding_*.json
   ```

3. **Aggregate data**
   ```bash
   python data_aggregator.py
   ```
   Expected: "Imported 3 sessions, 0 failed"

4. **View dashboard**
   ```bash
   streamlit run data_dashboard.py
   ```

5. **Verify in dashboard**
   - Overview: 3 sessions, 2 users, 12 turns
   - Users: Can select student_001 or student_002
   - All Sessions: Table shows all 3 sessions
   - Analytics: Shows case and personality stats

6. **Export data**
   - Click "Export to CSV"
   - Verify files in exports/

**Expected Result:** ✅ Complete workflow from training → data collection → analysis

---

## 9. Error Handling Tests

### Test: Invalid User ID (empty)
- Action: Don't enter user ID, try to start
- Expected: Error message, session doesn't start

### Test: Save without session
- Action: Click "End" without starting session
- Expected: No error, smooth transition to welcome screen

### Test: Database import of missing files
- Action: Delete a JSON file, run aggregator
- Expected: Reports error on missing file but continues with others

### Test: Dashboard with empty database
- Action: Delete database, open dashboard
- Expected: Shows "No sessions found" message

### Test: Invalid JSON file
- Action: Create malformed JSON in data folder, run aggregator
- Expected: Reports import error but continues with valid files

---

## 10. Performance Tests

### Test: Large Dataset
**Steps:**
1. Create 50 test sessions across 10 users
2. Run aggregator
3. Open dashboard

**Expected Result:** ✅ Dashboard loads without lag
- Metrics display correctly
- Charts render smoothly
- Filters respond quickly

### Test: Database Size
**Steps:**
1. Check size of vp_sessions.db after 50 sessions

**Expected Result:** ✅ Database < 1 MB (very efficient)

---

## 📋 Test Results Template

Print this section and fill it out:

```
TEST RESULTS - Multi-User VP System
Date: _______________
Tester: _______________

1. User ID Input System          [ ] PASS [ ] FAIL
2. User ID Validation            [ ] PASS [ ] FAIL
3. Auto-Save with Organization  [ ] PASS [ ] FAIL
4. Multiple Sessions Same User   [ ] PASS [ ] FAIL
5. Data Aggregator               [ ] PASS [ ] FAIL
6. Data Dashboard                [ ] PASS [ ] FAIL
7. Database Queries              [ ] PASS [ ] FAIL
8. End-to-End Workflow           [ ] PASS [ ] FAIL
9. Error Handling                [ ] PASS [ ] FAIL
10. Performance                  [ ] PASS [ ] FAIL

Overall Status: [ ] READY FOR DEPLOYMENT [ ] NEEDS FIXES

Issues Found:
- Issue 1: ___________________
- Issue 2: ___________________

Recommendations:
- ___________________
- ___________________
```

---

## 🎯 Quick Validation (5 minutes)

**If short on time, run this:**

1. ✅ `streamlit run app.py` - Enter user ID, start session, say 3 things, click End
2. ✅ Verify file saved in `data/[user_id]/`
3. ✅ `python data_aggregator.py` - Should import 1 session
4. ✅ `streamlit run data_dashboard.py` - Should show 1 session in Overview
5. ✅ Click Users tab, select your user, verify session listed

**Result:** If all 5 steps work, ✅ System is functional

---

## 🚀 Deployment Readiness Checklist

- [ ] User ID input working
- [ ] Sessions auto-saving to user folders
- [ ] Database aggregator working
- [ ] Dashboard displaying data
- [ ] CSV exports functional
- [ ] Documentation complete
- [ ] No critical errors in test runs
- [ ] Performance acceptable (< 2s load times)
- [ ] Ready for student distribution

**When all checked: ✅ READY FOR PRODUCTION**

