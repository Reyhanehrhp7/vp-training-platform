"""
Virtual Patient Interaction Engine

Manages multi-turn conversations with VPs, maintains conversation history,
and handles API communication with OpenAI.
"""

from openai import OpenAI
from typing import List, Dict, Optional, Tuple
from vp_builder import build_vp_system_prompt
from vp_cases import CASE_PROFILES
from vp_personalities import PERSONALITY_OVERLAYS


class VPConversationManager:
    """Manages a VP conversation session."""
    
    def __init__(self, case_key: str, personality_key: str, api_key: str):
        """
        Initialize a VP conversation.
        
        Args:
            case_key: Key from CASE_PROFILES (e.g., 'migraine', 'tia', 'parkinsons')
            personality_key: Key from PERSONALITY_OVERLAYS (e.g., 'neutral', 'anxious')
            api_key: OpenAI API key
        """
        if case_key not in CASE_PROFILES:
            raise ValueError(f"Unknown case: {case_key}. Available: {list(CASE_PROFILES.keys())}")
        if personality_key not in PERSONALITY_OVERLAYS:
            raise ValueError(f"Unknown personality: {personality_key}. Available: {list(PERSONALITY_OVERLAYS.keys())}")
        
        self.case_key = case_key
        self.personality_key = personality_key
        self.case_name = CASE_PROFILES[case_key]["case_name"]
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=api_key)
        
        # Build system prompt once
        self.system_prompt = build_vp_system_prompt(case_key, personality_key)
        
        # Conversation history (for API context)
        self.messages: List[Dict[str, str]] = []
        
    def get_vp_response(self, user_message: str) -> str:
        """
        Get VP response to user message.
        
        Args:
            user_message: Learner's input to the VP
            
        Returns:
            VP's response
        """
        # Add user message to history
        self.messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Get response from API
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": self.system_prompt},
                *self.messages
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        vp_response = response.choices[0].message.content
        
        # Add VP response to history
        self.messages.append({
            "role": "assistant",
            "content": vp_response
        })
        
        return vp_response
    
    def reset_conversation(self) -> None:
        """Reset conversation history (start over with same case/personality)."""
        self.messages = []
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get full conversation history."""
        return self.messages.copy()
    
    def get_turn_count(self) -> int:
        """Get number of user turns in conversation."""
        return len([m for m in self.messages if m["role"] == "user"])
    
    def export_session(self) -> Dict:
        """Export session data for analysis/logging."""
        return {
            "case": self.case_key,
            "case_name": self.case_name,
            "personality": self.personality_key,
            "turns": self.get_turn_count(),
            "history": self.get_conversation_history()
        }


def start_vp_session(case_key: str, personality_key: str, api_key: str) -> None:
    """
    Start an interactive VP session in the CLI.
    
    Args:
        case_key: Case to use
        personality_key: Personality to use
        api_key: OpenAI API key
    """
    # Initialize manager
    manager = VPConversationManager(case_key, personality_key, api_key)
    
    # Import feedback generator for real-time feedback
    from vp_feedback import FeedbackGenerator
    feedback_gen = FeedbackGenerator(api_key)
    
    print("\n" + "="*70)
    print(f"VIRTUAL PATIENT SESSION")
    print(f"Case: {manager.case_name}")
    print(f"Personality: {personality_key.upper()}")
    print("="*70)
    print("\nYou are the clinician. The patient is in the exam room.")
    print("Begin the interview whenever you're ready.")
    print("(Type 'quit' to exit, 'reset' to start over, 'history' to see transcript)\n")
    
    # Conversation loop - user starts
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("\n[Session ended]")
                session_data = manager.export_session()
                print(f"\nSession Summary:")
                print(f"  Case: {session_data['case_name']}")
                print(f"  Personality: {personality_key.upper()}")
                print(f"  Total turns: {session_data['turns']}")
                break
            
            if user_input.lower() == 'reset':
                manager.reset_conversation()
                print("\n[Conversation reset. Starting fresh...]\n")
                print("You are the clinician. The patient is in the exam room.")
                print("Begin the interview whenever you're ready.\n")
                continue
            
            if user_input.lower() == 'history':
                print("\n" + "="*70)
                print("CONVERSATION TRANSCRIPT")
                print("="*70)
                for msg in manager.get_conversation_history():
                    role = "You" if msg["role"] == "user" else "Patient"
                    print(f"\n{role}:\n{msg['content']}")
                print("\n" + "="*70 + "\n")
                continue
            
            # Get VP response
            print()
            vp_response = manager.get_vp_response(user_input)
            print(f"Patient: {vp_response}\n")
            
            # Generate and display immediate feedback
            print("="*70)
            print("TURN FEEDBACK")
            print("="*70)
            feedback = feedback_gen.generate_turn_feedback(
                case_name=manager.case_name,
                personality=personality_key,
                learner_utterance=user_input,
                vp_response=vp_response,
                turn_number=manager.get_turn_count()
            )
            print(f"\n{feedback['feedback']}\n")
            print("="*70 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n[Session interrupted]")
            break
        except Exception as e:
            print(f"\nError communicating with API: {e}")
            print("Please check your API key and try again.\n")


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*70)
    print("VIRTUAL PATIENT INTERACTION SYSTEM")
    print("="*70)
    
    # List available options
    print("\nAvailable Cases:")
    for key in CASE_PROFILES.keys():
        print(f"  - {key}: {CASE_PROFILES[key]['case_name']}")
    
    print("\nAvailable Personalities:")
    for key in PERSONALITY_OVERLAYS.keys():
        print(f"  - {key}")
    
    # Get inputs
    print("\n" + "-"*70)
    case_key = input("Select case (e.g., 'migraine'): ").strip().lower()
    personality_key = input("Select personality (e.g., 'neutral'): ").strip().lower()
    api_key = input("Enter your OpenAI API key: ").strip()
    
    if not case_key or not personality_key or not api_key:
        print("Error: All inputs required.")
        sys.exit(1)
    
    try:
        start_vp_session(case_key, personality_key, api_key)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
