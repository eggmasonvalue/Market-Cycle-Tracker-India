import streamlit as st

def load_css():
    """Inject custom CSS."""
    st.markdown("""
        <style>
        /* Main Container Padding */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* Metric Card Styling */
        .metric-card {
            background-color: #f9f9f9;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
            text-align: center;
        }

        .metric-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }

        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
        }

        /* Table Styling */
        .stDataFrame {
            font-size: 0.9em;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #f7f9fc;
        }

        /* Header Styling */
        h1, h2, h3 {
            color: #2c3e50;
        }

        /* Custom Button */
        div.stButton > button {
            background-color: #4A90E2;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 0.5rem 1rem;
        }
        div.stButton > button:hover {
            background-color: #357ABD;
            color: white;
        }

        </style>
    """, unsafe_allow_html=True)

def metric_card(label: str, value: str, delta: str = None, color: str = None):
    """
    Custom metric card component using HTML/CSS.
    Streamlit's st.metric is good but this allows more customization if needed.
    For now, st.metric is sufficient, but keeping this structure for potential expansion.
    """
    st.metric(label=label, value=value, delta=delta)
