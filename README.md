# Virtual Patient Training System

A comprehensive system for clinical communication skills training using AI-powered Virtual Patients (VPs). The system combines controllable patient simulations with rubric-based feedback on learner communication.

## Overview

### Core Components

1. **Case Profiles** (`vp_cases.py`)
   - Four clinically grounded cases: Migraine, TIA, Parkinson's, Astrocytoma
   - Each case includes relevant history, denials, and clinical rules
   - Information revealed progressively based on clinician questioning

2. **Personality Overlays** (`vp_personalities.py`)
   - Four personality modes: Neutral, Anxious, Demanding, Somatizing
   - Applied consistently to vary interpersonal difficulty
   - Maintains clinical accuracy while changing communication dynamic

3. **VP Builder** (`vp_builder.py`)
   - Composes case + personality into system prompts for GPT-4
   - Creates consistent VP behavior across conversations

4. **VP Interaction Engine** (`vp_interaction.py`)
   - Manages multi-turn conversations with VPs
   - Maintains conversation history
   - Handles API communication

5. **Feedback Generator** (`vp_feedback.py`)
   - Rubric-based evaluation of learner communication
   - Grounded in evidence-based clinical communication guidelines
   - Provides turn-level and session-level feedback
   - Links feedback to patient experience and actionable recommendations

6. **Main Application** (`main.py`)
   - Integrated menu-driven interface
   - Session management
   - Session export for research analysis

## Installation

### Prerequisites
- Python 3.8+
- OpenAI API key (with GPT-4 access)

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY="sk-..."
```

Or enter it interactively when prompted by the application.

## Usage

### Quick Start

```bash
python main.py
```

This launches the interactive menu where you can:
1. Start a new VP interaction session
2. View available cases and personalities
3. Exit

### Interactive Session Features

During a session with a VP, you can:

- **Continue the conversation**: Just type your input
- **`reset`**: Start a new conversation with the same VP
- **`history`**: View the full transcript of the current session
- **`quit`**: End the session and return to the menu

After a session ends, you can:
- Get comprehensive feedback on your communication
- Export the session data for analysis
- Return to the main menu to try a different case/personality

### Direct Script Usage

For programmatic use:

```python
from vp_interaction import VPConversationManager
from vp_feedback import FeedbackGenerator

# Create a VP conversation
manager = VPConversationManager(
    case_key="migraine",
    personality_key="anxious",
    api_key="sk-..."
)

# Get VP's initial response
initial = manager.get_vp_response("Hi there")

# Continue conversation
response = manager.get_vp_response("Tell me about your symptoms")

# Export session
data = manager.export_session()

# Generate feedback
feedback_gen = FeedbackGenerator("sk-...")
feedback = feedback_gen.generate_turn_feedback(
    case_name="Migraine",
    personality="anxious",
    learner_utterance="Tell me about your symptoms",
    vp_response="It's a bad headache on the right side...",
    turn_number=1
)
```

## Available Cases

### 1. Migraine without Aura
- **Patient**: 29F teacher
- **Chief complaint**: "I have the worst headache."
- **Key features**: Throbbing right-sided headache, photophobia, phonophobia
- **Clinical goal**: Elicit migraine diagnostic criteria

### 2. Transient Ischemic Attack (TIA)
- **Patient**: 64F with hypertension, hyperlipidemia, smoker
- **Chief complaint**: "My left arm went numb for 15 minutes."
- **Key features**: Focal neurologic symptoms (transient), full resolution
- **Clinical goal**: Recognize red flags, understand urgency

### 3. Parkinson's Disease
- **Patient**: 68M retired teacher
- **Chief complaint**: "My hand won't stop shaking."
- **Key features**: Resting tremor, bradykinesia, reduced facial expression
- **Clinical goal**: Distinguish Parkinson's from essential tremor

### 4. Low-Grade Astrocytoma
- **Patient**: Case structure ready for clinical content
- **Chief complaint**: [To be customized]
- **Clinical goal**: [To be defined]

## Available Personality Modes

### Neutral (Baseline)
- Calm, cooperative, polite
- Clear, direct answers
- Stable emotional tone
- Use for foundational clinical communication practice

### Anxious
- Expresses worry about serious causes
- Seeks reassurance
- Becomes calmer with empathy and clear explanations
- Good for practicing reassurance and shared decision-making

### Demanding
- Directive and time-pressured
- Pushes for immediate tests/treatments
- Frustrated by vague explanations
- Good for practicing boundary-setting and clear communication

### Somatizing
- Focuses heavily on bodily sensations
- Over-describes physical feelings
- Seeks validation
- Good for practicing patient-centered care

## Clinical Communication Rubric

Feedback is based on evidence-based guidelines:

1. **Open-Ended Questions**: Uses open questions to elicit concerns
2. **Active Listening**: Acknowledges, validates, reflects information
3. **Empathy & Rapport**: Recognizes emotional content, demonstrates understanding
4. **Information Gathering**: Systematic history, explores pertinent negatives
5. **Patient-Centered Approach**: Addresses patient concerns, invites participation
6. **Professionalism**: Clear communication, appropriate boundaries, respect

Each competency is rated:
- **Exemplary**: Excellent application of guideline
- **Proficient**: Appropriate, meets expectations
- **Developing**: Some effectiveness, gaps present
- **Needs Improvement**: Limited effectiveness, significant gaps

## Session Export Format

Sessions are exported as JSON with:
- Case information and clinical details
- Personality overlay details
- Full conversation transcript
- Metadata (start time, total turns, etc.)

Example structure:
```json
{
  "case": "migraine",
  "case_name": "Migraine without aura",
  "personality": "anxious",
  "turns": 8,
  "session_start": "2026-01-16T14:30:00",
  "session_end": "2026-01-16T14:45:00",
  "history": [
    {"role": "assistant", "content": "VP initial message"},
    {"role": "user", "content": "Learner message"},
    ...
  ]
}
```

## Research Applications

This system supports:
- **Controlled practice**: Consistent, reproducible VP behavior
- **Systematic feedback**: Independent, rubric-based evaluation
- **Comparative analysis**: Same learner, different personalities or cases
- **Skill progression**: Track improvement across multiple sessions
- **Data collection**: JSON exports for rigorous analysis

## Configuration

### OpenAI Settings

The system uses GPT-4 for:
- VP responses (temperature=0.7 for appropriate variation)
- Feedback generation (temperature=0.7 for consistent evaluation)

### Customization

To modify VP behavior:
1. Edit case prompts in `vp_cases.py`
2. Adjust personality overlays in `vp_personalities.py`
3. Modify feedback guidelines in `vp_feedback.py`

## Troubleshooting

### API Key Issues
- Ensure your OpenAI API key is valid and has GPT-4 access
- Check that your account has available credits

### Slow Responses
- GPT-4 API calls may take 5-30 seconds
- This is normal; the system indicates it's thinking

### Memory Issues
- If conversations become very long (100+ turns), API response time may increase
- Export and start a new session as needed

## Future Extensions

Readily extensible to:
- Additional clinical cases
- More personality variations
- Custom feedback rubrics
- Integration with LMS platforms
- Multimodal patient simulation (images, vital signs)
- Comparative analytics across learner populations

## Citation

If you use this system in research, please cite:
[Citation information to be added]

## Support

For issues or feature requests, contact: [Contact information]

---

**Note**: This system uses AI-generated patient responses and should be used for **educational training only**, not for clinical decision-making.
