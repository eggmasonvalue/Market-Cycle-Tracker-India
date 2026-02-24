import streamlit as st

def load_css():
    """Inject custom CSS. Keeping minimal overrides to avoid theme conflicts."""
    st.markdown("""
        <style>
        /* Main Container Padding */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* Table Styling */
        .stDataFrame {
            font-size: 0.9em;
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
