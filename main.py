"""
Virtual Patient Training System - Main Entry Point

Integrated system for VP interaction, feedback generation, and session management.
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path
from vp_interaction import VPConversationManager, start_vp_session
from vp_feedback import FeedbackGenerator, display_feedback
from vp_cases import CASE_PROFILES
from vp_personalities import PERSONALITY_OVERLAYS


API_KEY = os.getenv("OPENAI_API_KEY", "").strip()


class VPTrainingSession:
    """Complete training session with VP and feedback."""
    
    def __init__(self, case_key: str, personality_key: str, api_key: str):
        """Initialize training session."""
        self.case_key = case_key
        self.personality_key = personality_key
        self.api_key = api_key
        self.vp_manager = VPConversationManager(case_key, personality_key, api_key)
        self.feedback_generator = FeedbackGenerator(api_key)
        self.session_start = datetime.now()
    
    def run_interactive_session(self) -> None:
        """Run the full interactive session with VP."""
        start_vp_session(self.case_key, self.personality_key, self.api_key)
    
    def provide_feedback_on_last_turn(self) -> None:
        """Provide feedback on the most recent learner turn."""
        history = self.vp_manager.get_conversation_history()
        
        if len(history) < 2:
            print("\nNo turns to provide feedback on yet.")
            return
        
        # Find last learner turn
        learner_turn = None
        vp_response = None
        
        for i in range(len(history) - 1, -1, -1):
            if history[i]["role"] == "user" and learner_turn is None:
                learner_turn = history[i]["content"]
                # Get VP response after this
                if i + 1 < len(history):
                    vp_response = history[i + 1]["content"]
        
        if not learner_turn or not vp_response:
            print("\nCould not find last turn to provide feedback on.")
            return
        
        feedback = self.feedback_generator.generate_turn_feedback(
            case_name=self.vp_manager.case_name,
            personality=self.personality_key,
            learner_utterance=learner_turn,
            vp_response=vp_response,
            turn_number=self.vp_manager.get_turn_count()
        )
        
        display_feedback(feedback)
    
    def provide_session_summary(self) -> None:
        """Provide comprehensive feedback on entire session."""
        print("\n[Generating session summary feedback...]")
        
        summary = self.feedback_generator.generate_session_summary_feedback(
            case_name=self.vp_manager.case_name,
            personality=self.personality_key,
            conversation_history=self.vp_manager.get_conversation_history()
        )
        
        print("\n" + "="*70)
        print("SESSION SUMMARY FEEDBACK")
        print("="*70)
        print(summary.get("session_feedback", "No summary available"))
        print("="*70 + "\n")
    
    def export_session(self, filepath: str = None) -> str:
        """
        Export session data to JSON file.
        
        Args:
            filepath: Where to save. If None, generates timestamped filename.
            
        Returns:
            Path to exported file
        """
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_{self.case_key}_{self.personality_key}_{timestamp}.json"
            filepath = Path(filename)
        else:
            filepath = Path(filepath)
        
        session_data = self.vp_manager.export_session()
        session_data["personality_details"] = PERSONALITY_OVERLAYS[self.personality_key]
        session_data["case_details"] = CASE_PROFILES[self.case_key]
        session_data["session_start"] = self.session_start.isoformat()
        session_data["session_end"] = datetime.now().isoformat()
        
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return str(filepath)


def show_case_selection() -> str:
    """Display available cases and get user selection."""
    print("\n" + "="*70)
    print("SELECT CASE")
    print("="*70)
    
    cases = list(CASE_PROFILES.keys())
    for i, key in enumerate(cases, 1):
        profile = CASE_PROFILES[key]
        print(f"\n{i}. {key.upper()}")
        print(f"   Name: {profile['case_name']}")
        print(f"   Chief complaint: \"{profile['chief_complaint']}\"")
    
    while True:
        choice = input(f"\nSelect case (1-{len(cases)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(cases):
                return cases[idx]
        except ValueError:
            pass
        print(f"Invalid choice. Please enter a number between 1 and {len(cases)}.")


def show_personality_selection() -> str:
    """Display available personalities and get user selection."""
    print("\n" + "="*70)
    print("SELECT PERSONALITY")
    print("="*70)
    
    personalities = list(PERSONALITY_OVERLAYS.keys())
    for i, key in enumerate(personalities, 1):
        desc = PERSONALITY_OVERLAYS[key]
        lines = desc.strip().split('\n')
        print(f"\n{i}. {key.upper()}")
        for line in lines[1:4]:  # Show first few lines of description
            print(f"   {line}")
    
    while True:
        choice = input(f"\nSelect personality (1-{len(personalities)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(personalities):
                return personalities[idx]
        except ValueError:
            pass
        print(f"Invalid choice. Please enter a number between 1 and {len(personalities)}.")


def show_menu():
    """Display main menu."""
    print("\n" + "="*70)
    print("VIRTUAL PATIENT TRAINING SYSTEM")
    print("="*70)
    print("\nOptions:")
    print("  1. Start interactive session")
    print("  2. View all cases and personalities")
    print("  3. Exit")
    print("\nDuring session:")
    print("  - Type your communication to interact with the VP")
    print("  - Type 'reset' to restart the conversation")
    print("  - Type 'history' to view the transcript")
    print("  - Type 'quit' to end the session")
    print("-"*70 + "\n")

def main():
    """Main entry point."""
    
    # Check if API key is set
    if not API_KEY:
        print("\n" + "="*70)
        print("ERROR: API Key not configured")
        print("="*70)
        print("\nSet OPENAI_API_KEY before running this script.")
        print("PowerShell example: $env:OPENAI_API_KEY=\"sk-...\"")
        return
    
    print("\n" + "="*70)
    print("VIRTUAL PATIENT TRAINING SYSTEM")
    print("="*70)
    print("\nWelcome! Let's start your clinical communication training.")
    
    if not CASE_PROFILES:
        print("\nNo case profiles are configured. Add prompt files and restart the program.")
        return
    
    # Get case and personality upfront
    case_key = show_case_selection()
    personality_key = show_personality_selection()
    

    print("\n" + "-"*70)



    
    print(f"Starting session with {CASE_PROFILES[case_key]['case_name']} ({personality_key.upper()})...\n")
    
    try:
        # Create and run session
        session = VPTrainingSession(case_key, personality_key, API_KEY)
        session.run_interactive_session()
        
        # Offer post-session options
        print("\n" + "="*70)
        print("SESSION COMPLETE")
        print("="*70)
        
        while True:
            post_choice = input("\nWhat would you like to do?\n  1. Get session feedback\n  2. Export session\n  3. Start new session\n  4. Exit\n\nChoice (1-4): ").strip()
            
            if post_choice == "1":
                session.provide_session_summary()
            
            elif post_choice == "2":
                filepath = session.export_session()
                print(f"\n✓ Session exported to: {filepath}\n")
            
            elif post_choice == "3":
                main()  # Restart
                break
            
            elif post_choice == "4":
                print("\nThank you for training! Goodbye!")
                return
            
            else:
                print("Invalid choice. Please try again.")
    
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSession interrupted. Goodbye!")
        sys.exit(0)
