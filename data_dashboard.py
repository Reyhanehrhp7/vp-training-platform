import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from data_aggregator import DataAggregator

st.set_page_config(page_title="VP Sessions Dashboard", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .session-card {
        background: #f8f9fa;
        padding: 15px;
        border-left: 4px solid #667eea;
        border-radius: 5px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize database
@st.cache_resource
def get_aggregator():
    return DataAggregator("vp_sessions.db")

st.title("📊 VP Sessions Dashboard")

# Import button
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("**View and analyze all collected Virtual Patient training sessions**")
with col2:
    if st.button("🔄 Sync Database", help="Import latest session files"):
        with st.spinner("Syncing sessions..."):
            aggregator = get_aggregator()
            results = aggregator.import_all_sessions("data")
            st.success(f"✅ Imported {results['success']} sessions")

aggregator = get_aggregator()

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "👥 Users", "📋 All Sessions", "📊 Analytics"])

# Tab 1: Overview
with tab1:
    sessions = aggregator.get_all_sessions()
    
    if not sessions:
        st.info("No sessions found. Import sessions using the Sync button above.")
    else:
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Sessions", len(sessions))
        
        with col2:
            unique_users = len(set(s["user_id"] for s in sessions))
            st.metric("Unique Users", unique_users)
        
        with col3:
            total_turns = sum(s["total_turns"] or 0 for s in sessions)
            st.metric("Total Turns", total_turns)
        
        with col4:
            avg_turns = total_turns / len(sessions) if sessions else 0
            st.metric("Avg Turns/Session", f"{avg_turns:.1f}")
        
        # Case and Personality breakdown
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Sessions by Case")
            case_stats = aggregator.get_case_statistics()
            case_df = pd.DataFrame(case_stats)
            if not case_df.empty:
                st.bar_chart(case_df.set_index("case_name")["total_sessions"])
        
        with col2:
            st.subheader("Sessions by Personality")
            personality_stats = aggregator.get_personality_statistics()
            personality_df = pd.DataFrame(personality_stats)
            if not personality_df.empty:
                st.bar_chart(personality_df.set_index("personality_key")["total_sessions"])

# Tab 2: Users
with tab2:
    st.subheader("👥 User Statistics")
    
    users_query = "SELECT DISTINCT user_id FROM users ORDER BY user_id"
    users = aggregator.cursor.execute(users_query).fetchall()
    
    if not users:
        st.info("No users found.")
    else:
        # User search
        selected_user = st.selectbox("Select a user:", [u[0] for u in users])
        
        if selected_user:
            summary = aggregator.get_user_summary(selected_user)
            
            # User metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Sessions Completed", summary["total_sessions"])
            with col2:
                st.metric("Cases Practiced", summary["unique_cases"])
            with col3:
                st.metric("Personalities Tried", summary["unique_personalities"])
            with col4:
                st.metric("Total Interactions", summary["total_turns"])
            
            # User's sessions
            st.subheader(f"Sessions for {selected_user}")
            user_sessions = aggregator.get_sessions_by_user(selected_user)
            
            if user_sessions:
                sessions_df = pd.DataFrame(user_sessions)
                sessions_df["session_start"] = pd.to_datetime(sessions_df["session_start"])
                sessions_df = sessions_df.sort_values("session_start", ascending=False)
                
                st.dataframe(
                    sessions_df[["session_start", "case_name", "personality_key", "total_turns"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "session_start": st.column_config.DatetimeColumn("Start Time"),
                        "case_name": "Case",
                        "personality_key": "Personality",
                        "total_turns": st.column_config.NumberColumn("Turns")
                    }
                )

# Tab 3: All Sessions
with tab3:
    st.subheader("📋 All Sessions")
    
    sessions = aggregator.get_all_sessions()
    if sessions:
        sessions_df = pd.DataFrame(sessions)
        sessions_df["session_start"] = pd.to_datetime(sessions_df["session_start"])
        sessions_df = sessions_df.sort_values("session_start", ascending=False)
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            case_filter = st.multiselect("Filter by Case:", sessions_df["case_name"].unique())
        with col2:
            personality_filter = st.multiselect("Filter by Personality:", sessions_df["personality_key"].unique())
        with col3:
            user_filter = st.multiselect("Filter by User:", sessions_df["user_id"].unique())
        
        # Apply filters
        filtered_df = sessions_df.copy()
        if case_filter:
            filtered_df = filtered_df[filtered_df["case_name"].isin(case_filter)]
        if personality_filter:
            filtered_df = filtered_df[filtered_df["personality_key"].isin(personality_filter)]
        if user_filter:
            filtered_df = filtered_df[filtered_df["user_id"].isin(user_filter)]
        
        # Display table
        st.dataframe(
            filtered_df[["session_start", "user_id", "case_name", "personality_key", "total_turns"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "session_start": st.column_config.DatetimeColumn("Start Time"),
                "user_id": "User ID",
                "case_name": "Case",
                "personality_key": "Personality",
                "total_turns": st.column_config.NumberColumn("Turns")
            }
        )
        
        # Session details viewer
        st.subheader("📖 View Session Details")
        if filtered_df.empty:
            st.info("No sessions match the selected filters.")
        else:
            session_options = [
                f"{row['session_start'].strftime('%Y-%m-%d %H:%M')} | {row['user_id']} | {row['case_name']} ({row['personality_key']})"
                for _, row in filtered_df.iterrows()
            ]
            selected_session_str = st.selectbox("Select a session:", session_options)
            
            if selected_session_str:
                # Find the session
                for idx, row in filtered_df.iterrows():
                    if f"{row['session_start'].strftime('%Y-%m-%d %H:%M')} | {row['user_id']} | {row['case_name']} ({row['personality_key']})" == selected_session_str:
                        session_id = row["session_id"]
                        json_path = row.get("json_file_path")
                        
                        # Load and display session data
                        if json_path and Path(json_path).exists():
                            with open(json_path, 'r') as f:
                                session_data = json.load(f)
                            
                            # Display metadata
                            st.info(f"**Session ID:** {session_id}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**Case:** {session_data['session_metadata']['case_name']}")
                                st.markdown(f"**User:** {session_data['user_id']}")
                            with col2:
                                st.markdown(f"**Personality:** {session_data['session_metadata']['personality']}")
                                st.markdown(f"**Turns:** {session_data['session_metadata']['total_turns']}")
                            
                            # Display conversation
                            st.subheader("💬 Conversation")
                            for turn in session_data["transcript"]:
                                if turn["speaker"] == "Clinician":
                                    st.chat_message("user").write(turn["message"])
                                else:
                                    st.chat_message("assistant").write(turn["message"])
                        break

# Tab 4: Analytics
with tab4:
    st.subheader("📊 Analytics & Statistics")
    
    sessions = aggregator.get_all_sessions()
    if not sessions:
        st.info("No sessions found.")
    else:
        sessions_df = pd.DataFrame(sessions)
        
        # Case statistics
        st.subheader("Case Performance")
        case_stats = aggregator.get_case_statistics()
        if case_stats:
            case_df = pd.DataFrame(case_stats)
            st.dataframe(
                case_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "case_name": "Case",
                    "total_sessions": "Sessions",
                    "unique_users": "Users",
                    "avg_turns": st.column_config.NumberColumn("Avg Turns"),
                    "total_turns": "Total Turns"
                }
            )
        
        # Personality statistics
        st.subheader("Personality Performance")
        personality_stats = aggregator.get_personality_statistics()
        if personality_stats:
            personality_df = pd.DataFrame(personality_stats)
            st.dataframe(
                personality_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "personality_key": "Personality",
                    "total_sessions": "Sessions",
                    "unique_users": "Users",
                    "avg_turns": st.column_config.NumberColumn("Avg Turns"),
                    "total_turns": "Total Turns"
                }
            )
        
        # Export options
        st.subheader("💾 Export Data")
        if st.button("Export to CSV"):
            with st.spinner("Exporting..."):
                aggregator.export_to_csv("exports")
                st.success("✅ Data exported to exports/ directory")
                
                # Show available files
                export_dir = Path("exports")
                if export_dir.exists():
                    files = list(export_dir.glob("*.csv"))
                    st.markdown("**Available files:**")
                    for file in files:
                        st.markdown(f"- {file.name}")

# Footer
st.divider()
st.caption("💾 Database: vp_sessions.db | 🔄 Last updated: Real-time from database")
