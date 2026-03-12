"""
Feedback Generation System

Provides rubric-based, independent evaluation of learner communication behaviors
grounded in established clinical communication guidelines.
"""

from openai import OpenAI
from typing import Dict, List
from enum import Enum


class FeedbackRubric(Enum):
    """Communication competency rubric levels."""
    EXEMPLARY = "Exemplary"
    PROFICIENT = "Proficient"
    DEVELOPING = "Developing"
    NEEDS_IMPROVEMENT = "Needs Improvement"


CLINICAL_COMMUNICATION_GUIDELINES = """
Evidence-based clinical communication guidelines used for feedback:

1. OPEN-ENDED QUESTIONS
   - Uses open-ended questions to elicit patient concerns
   - Avoids premature narrowing of diagnostic scope
   - Allows patient autonomy in symptom description

2. ACTIVE LISTENING
   - Acknowledges and validates patient concerns
   - Reflects back key information
   - Demonstrates attentiveness through responses

3. EMPATHY & RAPPORT
   - Recognizes and responds to emotional content
   - Uses appropriate tone and pacing
   - Demonstrates understanding of patient perspective

4. INFORMATION GATHERING
   - Gathers relevant history systematically
   - Explores pertinent negatives appropriately
   - Clarifies symptom characteristics (onset, duration, severity)

5. PATIENT-CENTERED APPROACH
   - Addresses patient's concerns, not just clinician agenda
   - Explains clinical reasoning when appropriate
   - Invites patient participation in decision-making

6. PROFESSIONALISM & COMMUNICATION
   - Uses clear, jargon-free language
   - Maintains appropriate boundaries
   - Communicates with respect and without judgment
"""


class FeedbackGenerator:
    """Generates rubric-based feedback on learner communication."""
    
    def __init__(self, api_key: str):
        """Initialize with OpenAI API key."""
        self.client = OpenAI(api_key=api_key)
    
    def generate_turn_feedback(
        self,
        case_name: str,
        personality: str,
        learner_utterance: str,
        vp_response: str,
        turn_number: int = 1
    ) -> Dict[str, str]:
        """
        Generate feedback on a single learner turn.
        
        Args:
            case_name: Clinical case being practiced
            personality: Patient personality overlay
            learner_utterance: What the learner said
            vp_response: VP's response to the learner
            turn_number: Which turn in the interaction
            
        Returns:
            Dictionary with feedback, rubric level, and recommendations
        """
        
        feedback_prompt = f"""
You are an expert clinical communication educator providing feedback on a learner's 
interaction with a Virtual Patient.

CASE CONTEXT:
- Clinical case: {case_name}
- Patient personality: {personality}
- Turn number: {turn_number}

CLINICAL COMMUNICATION GUIDELINES:
{CLINICAL_COMMUNICATION_GUIDELINES}

LEARNER'S COMMUNICATION:
"{learner_utterance}"

PATIENT RESPONSE:
"{vp_response}"

Provide structured feedback:

1. STRENGTHS (what the learner did well):
   - List 2-3 specific strengths grounded in clinical communication guidelines

2. AREAS FOR GROWTH (what could improve):
   - List 1-2 specific areas for development

3. RUBRIC LEVEL: Choose ONE
   - Exemplary (excellent communication, strong clinical decision-making)
   - Proficient (appropriate communication, meets expectations)
   - Developing (some effective communication, but gaps present)
   - Needs Improvement (limited effectiveness, significant gaps)

4. SPECIFIC RECOMMENDATION:
   - One actionable suggestion for the next interaction

Format your response with clear section headers.
"""
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": feedback_prompt}
            ],
            temperature=0.7,
            max_tokens=600
        )
        
        feedback_text = response.choices[0].message.content
        
        return {
            "turn": turn_number,
            "learner_input": learner_utterance,
            "vp_response": vp_response,
            "feedback": feedback_text
        }
    
    def generate_session_summary_feedback(
        self,
        case_name: str,
        personality: str,
        conversation_history: List[Dict[str, str]]
    ) -> Dict:
        """
        Generate comprehensive feedback on entire conversation session.
        
        Args:
            case_name: Clinical case
            personality: Patient personality overlay
            conversation_history: Full conversation history (from VPConversationManager)
            
        Returns:
            Dictionary with session-level analysis
        """
        
        # Extract learner messages only
        learner_turns = [msg["content"] for msg in conversation_history if msg["role"] == "user"]
        
        if not learner_turns:
            return {"error": "No learner turns to analyze"}
        
        # Prepare transcript for analysis
        transcript = "INTERACTION TRANSCRIPT:\n"
        for msg in conversation_history:
            role = "LEARNER" if msg["role"] == "user" else "PATIENT"
            transcript += f"\n{role}:\n{msg['content']}\n"
        
        summary_prompt = f"""
You are an expert clinical communication educator providing comprehensive feedback
on a learner's full interaction session with a Virtual Patient.

CASE: {case_name}
PATIENT PERSONALITY: {personality}
NUMBER OF LEARNER TURNS: {len(learner_turns)}

CLINICAL COMMUNICATION GUIDELINES:
{CLINICAL_COMMUNICATION_GUIDELINES}

{transcript}

Provide a comprehensive session summary with:

1. OVERALL ASSESSMENT:
   - General strengths across the session
   - General areas for development
   - Quality of information gathering
   - Quality of patient engagement

2. COMPETENCY ANALYSIS (for each of the 6 guidelines):
   - Rate: Exemplary, Proficient, Developing, or Needs Improvement
   - Brief justification with examples from the conversation

3. SPECIFIC PATTERNS OBSERVED:
   - Communication patterns that emerged
   - How the learner adapted (or didn't) to patient personality

4. KEY RECOMMENDATIONS FOR NEXT PRACTICE:
   - 2-3 prioritized areas for focused improvement
   - Specific strategies to implement

5. STRENGTHS TO MAINTAIN:
   - 2-3 effective approaches to build upon

Keep feedback constructive, specific, and grounded in clinical communication evidence.
"""
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.7,
            max_tokens=1200
        )
        
        summary_text = response.choices[0].message.content
        
        # Extract competency ratings and calculate overall grade
        competency_scores = self._extract_competency_scores(summary_text)
        overall_grade = self._calculate_overall_grade(competency_scores)
        
        return {
            "case": case_name,
            "personality": personality,
            "total_turns": len(learner_turns),
            "session_feedback": summary_text,
            "conversation_length": len(conversation_history),
            "competency_scores": competency_scores,
            "overall_grade": overall_grade
        }
    
    def _extract_competency_scores(self, feedback_text: str) -> Dict[str, str]:
        """
        Extract competency ratings from feedback text.
        
        Args:
            feedback_text: Full feedback text with competency analysis
            
        Returns:
            Dictionary mapping competency names to ratings
        """
        competencies = {
            "Open-Ended Questions": "Not rated",
            "Active Listening": "Not rated",
            "Empathy & Rapport": "Not rated",
            "Information Gathering": "Not rated",
            "Patient-Centered Approach": "Not rated",
            "Professionalism & Communication": "Not rated"
        }
        
        ratings = ["Exemplary", "Proficient", "Developing", "Needs Improvement"]
        
        # Try to find each competency and its rating
        for competency in competencies.keys():
            # Look for the competency name (case-insensitive)
            competency_lower = competency.lower()
            feedback_lower = feedback_text.lower()
            
            competency_pos = feedback_lower.find(competency_lower)
            if competency_pos != -1:
                # Search for rating after the competency mention
                search_window = feedback_text[competency_pos:competency_pos+200]
                for rating in ratings:
                    if rating in search_window:
                        competencies[competency] = rating
                        break
        
        return competencies
    
    def _calculate_overall_grade(self, competency_scores: Dict[str, str]) -> Dict:
        """
        Calculate overall grade based on competency scores.
        
        Args:
            competency_scores: Dictionary of competency ratings
            
        Returns:
            Dictionary with letter grade, percentage, and level
        """
        # Score mapping
        score_map = {
            "Exemplary": 4,
            "Proficient": 3,
            "Developing": 2,
            "Needs Improvement": 1,
            "Not rated": 0
        }
        
        # Get all scores, including "Not rated" but exclude them from calculation
        scores = [score_map.get(rating, 0) for rating in competency_scores.values() if rating != "Not rated"]
        
        # Check if we have at least half of the competencies rated
        total_competencies = len(competency_scores)
        rated_competencies = len(scores)
        
        if rated_competencies < total_competencies * 0.5:  # Less than 50% rated
            return {
                "letter_grade": "N/A",
                "percentage": 0,
                "level": "Not enough data",
                "average_score": 0,
                "competency_scores": competency_scores
            }
        
        average_score = sum(scores) / len(scores) if scores else 0
        percentage = (average_score / 4) * 100 if average_score > 0 else 0
        
        # Grade thresholds
        if percentage >= 90:
            letter_grade = "A"
            level = "Exemplary"
        elif percentage >= 80:
            letter_grade = "B"
            level = "Proficient"
        elif percentage >= 70:
            letter_grade = "C"
            level = "Developing"
        elif percentage >= 60:
            letter_grade = "D"
            level = "Needs Improvement"
        else:
            letter_grade = "F"
            level = "Below Expectations"
        
        return {
            "letter_grade": letter_grade,
            "percentage": round(percentage, 1),
            "level": level,
            "average_score": round(average_score, 2),
            "competency_scores": competency_scores
        }


def display_feedback(feedback: Dict) -> None:
    """Pretty-print feedback to console."""
    print("\n" + "="*70)
    print("FEEDBACK ON YOUR COMMUNICATION")
    print("="*70)
    print(feedback.get("feedback", feedback.get("session_feedback", "No feedback available")))
    print("="*70 + "\n")


if __name__ == "__main__":
    # Example usage (for testing)
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Set OPENAI_API_KEY environment variable to test feedback generation")
    else:
        generator = FeedbackGenerator(api_key)
        
        # Example turn feedback
        feedback = generator.generate_turn_feedback(
            case_name="Migraine without aura",
            personality="anxious",
            learner_utterance="Can you tell me more about when this started and what it feels like?",
            vp_response="It started this morning. The pain is on my right side, and I've never had one this bad before. I'm really worried it might be something serious."
        )
        
        print("Example Turn Feedback:")
        display_feedback(feedback)
