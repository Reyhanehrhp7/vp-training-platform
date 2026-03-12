"""
Virtual Patient Session Data - JSON Format Guide

Example exported session file and how to read it.
"""

import json
from pathlib import Path

# EXAMPLE JSON FILE STRUCTURE
EXAMPLE_SESSION = {
    "case": "migraine",
    "case_name": "Migraine without aura",
    "personality": "anxious",
    "turns": 4,
    "session_start": "2026-01-16T14:30:00.123456",
    "session_end": "2026-01-16T14:45:32.654321",
    "history": [
        {
            "role": "user",
            "content": "Hi, what brought you in today?"
        },
        {
            "role": "assistant",
            "content": "I have the worst headache. It started this morning and I'm really worried it might be something serious."
        },
        {
            "role": "user",
            "content": "Can you tell me more about the pain? Where exactly is it?"
        },
        {
            "role": "assistant",
            "content": "It's on my right side, here. It's throbbing and I can't stand bright light. Every time I move, it gets worse."
        }
    ],
    "case_details": {
        "case_name": "Migraine without aura",
        "chief_complaint": "I have the worst headache.",
        "case_prompt": "Clinical case: Migraine without aura..."
    },
    "personality_details": "Personality: Anxious\n- Expresses worry about serious causes..."
}


def read_session_file(filepath: str) -> dict:
    """
    Read and parse a session JSON file.
    
    Args:
        filepath: Path to the .json file
        
    Returns:
        Dictionary containing session data
    """
    with open(filepath, 'r') as f:
        session = json.load(f)
    return session


def extract_conversation(session: dict) -> list:
    """
    Extract conversation turns from session.
    
    Args:
        session: Session dictionary
        
    Returns:
        List of conversation turns with speaker and content
    """
    turns = []
    for msg in session.get("history", []):
        turn = {
            "speaker": "Clinician" if msg["role"] == "user" else "Patient",
            "message": msg["content"]
        }
        turns.append(turn)
    return turns


def get_session_metadata(session: dict) -> dict:
    """Get session metadata."""
    from datetime import datetime
    
    start = datetime.fromisoformat(session["session_start"])
    end = datetime.fromisoformat(session["session_end"])
    duration = end - start
    
    return {
        "case": session["case"],
        "case_name": session["case_name"],
        "personality": session["personality"],
        "total_turns": session["turns"],
        "duration_seconds": duration.total_seconds(),
        "duration_formatted": f"{int(duration.total_seconds() // 60)}:{int(duration.total_seconds() % 60):02d}",
        "start_time": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end.strftime("%Y-%m-%d %H:%M:%S")
    }


def print_session_summary(filepath: str) -> None:
    """
    Pretty print a session summary.
    
    Args:
        filepath: Path to the .json file
    """
    session = read_session_file(filepath)
    metadata = get_session_metadata(session)
    
    print("\n" + "="*70)
    print("SESSION SUMMARY")
    print("="*70)
    print(f"Case:              {metadata['case_name']}")
    print(f"Personality:       {metadata['personality'].upper()}")
    print(f"Total Turns:       {metadata['total_turns']}")
    print(f"Duration:          {metadata['duration_formatted']}")
    print(f"Start Time:        {metadata['start_time']}")
    print(f"End Time:          {metadata['end_time']}")
    print("="*70 + "\n")
    
    print("CONVERSATION TRANSCRIPT")
    print("="*70)
    turns = extract_conversation(session)
    for i, turn in enumerate(turns, 1):
        print(f"\nTurn {i}: {turn['speaker']}")
        print(f"{turn['message']}\n")
    print("="*70)


def export_to_csv(filepath: str, output_csv: str = None) -> str:
    """
    Export session data to CSV.
    
    Args:
        filepath: Path to the .json file
        output_csv: Output CSV filename (optional)
        
    Returns:
        Path to created CSV file
    """
    import csv
    
    session = read_session_file(filepath)
    turns = extract_conversation(session)
    
    if output_csv is None:
        output_csv = filepath.replace('.json', '.csv')
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header with metadata
        writer.writerow(['Session Metadata'])
        writer.writerow(['Case', session['case']])
        writer.writerow(['Case Name', session['case_name']])
        writer.writerow(['Personality', session['personality']])
        writer.writerow(['Total Turns', session['turns']])
        writer.writerow(['Start Time', session['session_start']])
        writer.writerow(['End Time', session['session_end']])
        writer.writerow([])  # Blank row
        
        # Conversation
        writer.writerow(['Turn', 'Speaker', 'Message'])
        for i, turn in enumerate(turns, 1):
            writer.writerow([i, turn['speaker'], turn['message']])
    
    return output_csv


def analyze_session(filepath: str) -> dict:
    """
    Analyze session statistics.
    
    Args:
        filepath: Path to the .json file
        
    Returns:
        Dictionary with analysis metrics
    """
    session = read_session_file(filepath)
    turns = extract_conversation(session)
    
    clinician_messages = [t for t in turns if t['speaker'] == 'Clinician']
    patient_messages = [t for t in turns if t['speaker'] == 'Patient']
    
    clinician_avg_length = sum(len(m['message'].split()) for m in clinician_messages) / len(clinician_messages) if clinician_messages else 0
    patient_avg_length = sum(len(m['message'].split()) for m in patient_messages) / len(patient_messages) if patient_messages else 0
    
    analysis = {
        "total_turns": session["turns"],
        "clinician_turns": len(clinician_messages),
        "patient_turns": len(patient_messages),
        "clinician_avg_words": round(clinician_avg_length, 1),
        "patient_avg_words": round(patient_avg_length, 1),
        "case": session["case"],
        "personality": session["personality"],
        "duration_seconds": (
            (datetime.fromisoformat(session["session_end"]) - 
             datetime.fromisoformat(session["session_start"])).total_seconds()
        )
    }
    
    return analysis


# USAGE EXAMPLES
if __name__ == "__main__":
    from datetime import datetime
    
    print("\n" + "="*70)
    print("VIRTUAL PATIENT SESSION DATA - USAGE GUIDE")
    print("="*70)
    
    print("\n1. READ A SESSION FILE")
    print("-" * 70)
    print("""
    from json_reader import read_session_file
    
    session = read_session_file('session_migraine_anxious_20260116_143000.json')
    print(session['case'])  # Output: migraine
    print(session['turns'])  # Output: 4
    """)
    
    print("\n2. EXTRACT CONVERSATION")
    print("-" * 70)
    print("""
    from json_reader import extract_conversation
    
    turns = extract_conversation(session)
    for turn in turns:
        print(f"{turn['speaker']}: {turn['message']}")
    """)
    
    print("\n3. GET SESSION METADATA")
    print("-" * 70)
    print("""
    from json_reader import get_session_metadata
    
    metadata = get_session_metadata(session)
    print(metadata['duration_formatted'])  # Output: 15:32
    print(metadata['case_name'])  # Output: Migraine without aura
    """)
    
    print("\n4. PRINT SUMMARY")
    print("-" * 70)
    print("""
    from json_reader import print_session_summary
    
    print_session_summary('session_migraine_anxious_20260116_143000.json')
    """)
    
    print("\n5. EXPORT TO CSV")
    print("-" * 70)
    print("""
    from json_reader import export_to_csv
    
    csv_file = export_to_csv('session_migraine_anxious_20260116_143000.json')
    print(f"Exported to: {csv_file}")
    """)
    
    print("\n6. ANALYZE SESSION")
    print("-" * 70)
    print("""
    from json_reader import analyze_session
    
    analysis = analyze_session('session_migraine_anxious_20260116_143000.json')
    print(f"Clinician turns: {analysis['clinician_turns']}")
    print(f"Patient turns: {analysis['patient_turns']}")
    print(f"Avg clinician words: {analysis['clinician_avg_words']}")
    """)
    
    print("\n" + "="*70)
    print("JSON FILE STRUCTURE")
    print("="*70)
    print(json.dumps(EXAMPLE_SESSION, indent=2))
