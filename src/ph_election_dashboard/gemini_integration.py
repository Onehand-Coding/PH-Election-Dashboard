import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai

from config import logger

load_dotenv()

def configure_gemini():
    """
    Configures the Gemini API with the API key from environment variables.
    Returns:
        GenerativeModel or None: Configured model if successful, None otherwise.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables.")
        return None
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-pro")
    except Exception as e:
        logger.error(f"Error configuring Gemini API: {e}")
        return None

def generate_fallback_summary(data_df, election_type, position_filter=None, location_filters=None):
    """
    Generates a fallback summary when Gemini API is unavailable.
    Args:
        data_df (pd.DataFrame): Filtered election data.
        election_type (str): Type of election (national, local, barangay).
        position_filter (str, optional): Selected position filter.
        location_filters (dict, optional): Selected location filters.
    Returns:
        str: Markdown-formatted summary.
    """
    if data_df.empty:
        return "No data available to summarize."

    summary = [f"**{election_type.capitalize()} Election Summary**"]
    if position_filter and position_filter != "All":
        summary.append(f" (Position: {position_filter})")
    if location_filters:
        loc_info = [f"{k}: {v}" for k, v in location_filters.items() if v != "All"]
        if loc_info:
            summary.append(f" ({', '.join(loc_info)})")

    top_candidates = data_df.sort_values(by="total_votes", ascending=False).head(3)
    summary.append("\n**Top Candidates**")
    for _, row in top_candidates.iterrows():
        party_info = f" ({row.get('party', 'N/A')})" if "party" in data_df.columns else ""
        summary.append(f"- {row['candidate_name']}{party_info}: {row['total_votes']:,} votes")

    if "party" in data_df.columns and data_df["party"].nunique() > 1:
        party_share = data_df.groupby("party")["total_votes"].sum() / data_df["total_votes"].sum() * 100
        summary.append("\n**Party Vote Share**")
        for party, share in party_share.items():
            summary.append(f"- {party}: {share:.1f}%")

    if len(top_candidates) >= 2:
        vote_diff = top_candidates.iloc[0]["total_votes"] - top_candidates.iloc[1]["total_votes"]
        total_votes = top_candidates["total_votes"].sum()
        if total_votes > 0 and (vote_diff / total_votes * 100) < 5:
            summary.append(f"\n**Close Race Alert**: The top two candidates are within {vote_diff:,} votes (<5% of total).")

    return "\n".join(summary)

def generate_election_summary(data_df, election_type, position_filter=None, location_filters=None):
    """
    Generates an election summary using Gemini API or fallback.
    Args:
        data_df (pd.DataFrame): Filtered election data.
        election_type (str): Type of election (national, local, barangay).
        position_filter (str, optional): Selected position filter.
        location_filters (dict, optional): Selected location filters.
    Returns:
        str: Markdown-formatted summary.
    """
    model = configure_gemini()
    if not model:
        logger.warning("Using fallback summary due to Gemini API configuration failure.")
        return generate_fallback_summary(data_df, election_type, position_filter, location_filters)

    if data_df.empty:
        return "No data available to summarize."

    summary_df = data_df.copy()
    if position_filter and position_filter != "All":
        summary_df = summary_df[summary_df["position"] == position_filter]
    if location_filters:
        for col, val in location_filters.items():
            if val != "All" and col in summary_df.columns:
                summary_df = summary_df[summary_df[col] == val]

    data_json = summary_df.head(10).to_json(orient="records", indent=2)
    location_str = ", ".join([f"{k}: {v}" for k, v in (location_filters or {}).items() if v != "All"]) or "N/A"
    prompt = f"""
    Summarize the {election_type} election results for {position_filter or 'all positions'}.
    Data: {data_json}
    Include:
    - Top 3 candidates with vote counts.
    - Notable party performance.
    - Close races (vote difference <5%).
    - Regional insights if applicable: {location_str}.
    Keep it concise, 3-5 bullet points, in Markdown format.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        logger.warning("Falling back to local summary generation.")
        return generate_fallback_summary(data_df, election_type, position_filter, location_filters)
