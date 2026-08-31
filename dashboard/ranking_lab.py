import streamlit as st

st.set_page_config(
    page_title="JobAgent Ranking Lab",
    layout="wide",
)

st.title("JobAgent Ranking Lab")
st.caption("Visualization and experimentation environment for the JobAgent ranking engine.")

st.divider()

st.subheader("Ranking Engine")

st.info(
    "The ranking engine is currently isolated from this dashboard. "
    "We will connect the real scoring pipeline after auditing the current implementation."
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Role Weight", "30%")

with col2:
    st.metric("Skill Weight", "40%")

with col3:
    st.metric("Experience Weight", "20%")

with col4:
    st.metric("Location Weight", "10%")

st.divider()

st.subheader("Coming next")

st.write(
    """
    - Rank comparison
    - Individual job score breakdown
    - Score contribution visualization
    - Weight experimentation
    - Pairwise job comparison
    - Ranking anomaly detection
    """
)

st.warning(
    "Do not use these displayed weights as the current source of truth. "
    "They represent the previously documented ranking configuration and will be "
    "verified against the actual code later."
)