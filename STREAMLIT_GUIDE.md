# Virtual Patient Training System - Web Interface

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Streamlit App

```bash
streamlit run app.py
```

The application will open in your web browser at `http://localhost:8501`

## Features

### 🎯 Setup
- **Case Selection**: Choose from 4 clinical cases via dropdown
- **Personality Selection**: Select patient personality (Neutral, Anxious, Demanding, Somatizing)
- **API Configuration**: Enter your OpenAI API key securely

### 💬 Interview Interface
- **Chat-like Conversation**: Natural dialogue with the virtual patient
- **Session Tracking**: Monitor case, personality, and turn count
- **Real-time Feedback**: Get immediate feedback on each communication turn

### 📋 Feedback System
- **Turn-level Feedback**: Strengths, growth areas, rubric level, and recommendations after each turn
- **Session Summary**: Comprehensive analysis across all 6 communication competencies
- **Evidence-based Guidelines**: Feedback grounded in clinical communication best practices

### 💾 Session Management
- **Reset**: Start over with the same case and personality
- **Export**: Download session as JSON for analysis
- **Session History**: View full conversation transcript

## How to Use

1. **Start**: Click the "▶ Start Session" button in the sidebar
2. **Converse**: Type your clinical question or statement
3. **Review**: Read patient response and immediate feedback
4. **Continue**: Ask follow-up questions
5. **Export**: When done, click "💾 Export Session" to save

## Clinical Cases

### Migraine without Aura
- 29-year-old teacher with severe right-sided headache
- Key skills: Migraine diagnostic criteria, symptom characterization

### Transient Ischemic Attack (TIA)
- 64-year-old with hypertension/hyperlipidemia, transient numbness
- Key skills: Red flag recognition, urgency assessment

### Parkinson's Disease
- 68-year-old with resting tremor and bradykinesia
- Key skills: Movement disorder assessment, differential diagnosis

### Low-Grade Astrocytoma
- Neurological case for advanced learners
- Key skills: Case-specific clinical reasoning

## Patient Personalities

- **Neutral**: Cooperative, clear responses (baseline)
- **Anxious**: Worried, seeks reassurance (tests empathy)
- **Demanding**: Time-pressured, expects immediate action (tests boundaries)
- **Somatizing**: Focuses on bodily sensations, seeks validation (tests patient-centeredness)

## Communication Rubric

Feedback evaluates 6 evidence-based competencies:

1. **Open-Ended Questions** - Eliciting patient concerns
2. **Active Listening** - Acknowledgment and validation
3. **Empathy & Rapport** - Emotional recognition and connection
4. **Information Gathering** - Systematic history taking
5. **Patient-Centered Approach** - Addressing patient agenda
6. **Professionalism** - Clear communication and boundaries

Each is rated: Exemplary | Proficient | Developing | Needs Improvement

## Tips for Best Results

- Ask open-ended questions first ("Tell me about...")
- Listen carefully to patient responses
- Ask pertinent negatives (especially for TIA)
- Pay attention to patient's emotional state (personality matters!)
- Adapt your approach based on feedback

## System Requirements

- Python 3.8+
- OpenAI API key with GPT-4 access
- Internet connection

## Troubleshooting

**"No module named 'openai'"**
```bash
pip install --upgrade openai
```

**"No module named 'streamlit'"**
```bash
pip install streamlit streamlit-chat
```

**API Key Issues**
- Check that your key starts with "sk-"
- Verify you have GPT-4 access in your OpenAI account
- Ensure account has available credits

**Slow Responses**
- GPT-4 API calls typically take 5-30 seconds
- This is normal behavior
- Check your internet connection

## Data Export Format

Sessions export as JSON containing:
- Full conversation transcript
- Case and personality details
- Session metadata (start/end times)
- Turn count
- Ready for analysis and research

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify your API key and internet connection
3. Review the main README.md for system overview
