from typing import Dict, Any
import os
import json
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

genai.configure(api_key=GEMINI_API_KEY)

PROMPT_SYSTEM = (
    "You are an expert AI Career Mentor. Based on the student's input, generate a structured, "
    "personalized career roadmap. Respond ONLY in JSON with these fields:\n"
    "- summary\n"
    "- target_role\n"
    "- experience_level\n"
    "- timeline (MUST be a list of objects. Each object MUST contain period, goals, milestones.)\n"
    "- skills_by_stage\n"
    "- projects\n"
    "- tools_and_tech\n"
    "- motivation_and_tips\n"
    "Output must be valid JSON with no explanation outside the JSON."
)

PROMPT_USER_TEMPLATE = (
    "Student Name: {name}\n"
    "Current Experience: {experience}\n"
    "Target Role: {role}\n"
    "Career Goal: {goal}\n"
    "Additional Context: {context}"
)

def safe_json_loads(s: str) -> Dict[str, Any]:
    try:
        return json.loads(s)
    except Exception:
        import re
        match = re.search(r"\{.*\}", s, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
    return {"error": "Invalid JSON", "raw": s}

def call_gemini(system_prompt: str, user_prompt: str) -> str:
    model = genai.GenerativeModel(model_name=GEMINI_MODEL)
    full_prompt = system_prompt + "\n\nUser Input:\n" + user_prompt
    response = model.generate_content(full_prompt)
    return response.text

def generate_roadmap(name, experience, role, goal, context):
    user_prompt = PROMPT_USER_TEMPLATE.format(
        name=name, experience=experience, role=role, goal=goal, context=context
    )
    response = call_gemini(PROMPT_SYSTEM, user_prompt)
    parsed = safe_json_loads(response)
    parsed.setdefault("metadata", {})
    parsed["metadata"]["raw_output"] = response
    parsed["metadata"]["created_at"] = datetime.utcnow().isoformat() + "Z"
    return parsed

def display_as_text(data):
    """Convert dict or list into readable text."""
    text_output = ""
    if isinstance(data, dict):
        for key, value in data.items():
            text_output += f"**{key}**\n"
            if isinstance(value, list):
                for idx, item in enumerate(value, 1):
                    text_output += f"{idx}. {item}\n"
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    text_output += f"{sub_key}:\n"
                    if isinstance(sub_value, list):
                        for idx, item in enumerate(sub_value, 1):
                            text_output += f"  {idx}. {item}\n"
                    else:
                        text_output += f"  {sub_value}\n"
            else:
                text_output += f"{value}\n"
            text_output += "\n"
    elif isinstance(data, list):
        for idx, item in enumerate(data, 1):
            if isinstance(item, dict):
                name = item.get("name", "")
                desc = item.get("description", "")
                skills = item.get("skills_used", "")
                text_output += f"**{idx}. {name}**  \n"
                if desc:
                    text_output += f"{desc}  \n"
                if skills:
                    text_output += f"Skills Used: {skills}  \n\n"
            else:
                text_output += f"{idx}. {item}\n\n"
    else:
        text_output += str(data)
    return text_output

st.set_page_config(page_title="AI Career Roadmap Generator", layout="wide")
st.title("AI-Powered Career Roadmap Generator")
st.caption("Gemini 2.5 Flash • Streamlit • Python 3")

with st.sidebar:
    st.header("Input Details")
    name = st.text_input("Your Name", value=os.getenv("DEMO_NAME", "Student"))
    experience = st.selectbox(
        "Experience Level",
        ["No experience", "0-1 years", "1-3 years", "3+ years", "Career Switcher"],
    )
    role = st.text_input("Target Job Role", value=os.getenv("DEMO_ROLE", "Data Scientist"))
    goal = st.text_input("Career Goal", value=os.getenv("DEMO_GOAL", "Land a data scientist role"))
    context = st.text_area("Skills you know / constraints", value=os.getenv("DEMO_CONTEXT", "Python"))
    submitted = st.button("Generate Roadmap")

if submitted:
    with st.spinner("Generating roadmap..."):
        roadmap = generate_roadmap(name, experience, role, goal, context)
        st.session_state["roadmap"] = roadmap

if "roadmap" in st.session_state:
    roadmap = st.session_state["roadmap"]

    if "error" in roadmap:
        st.error("Error: " + str(roadmap["error"]))
    else:
        st.success("Roadmap generated successfully!")

        st.header(roadmap.get("target_role", "Career Roadmap"))

        st.subheader("Summary")
        st.write(roadmap.get("summary", ""))

        st.subheader("Skills by Stage")
        skills_text = display_as_text(roadmap.get("skills_by_stage", {}))
        st.markdown(skills_text)

        st.subheader("Timeline")
        timeline = roadmap.get("timeline", [])
        if isinstance(timeline, list):
            for block in timeline:
                if isinstance(block, dict):
                    with st.expander(block.get("period", "Timeline Block")):
                        goals = block.get("goals", [])
                        milestones = block.get("milestones", [])
                        if goals:
                            st.write("**Goals:**")
                            for idx, goal_item in enumerate(goals, 1):
                                st.write(f"{idx}. {goal_item}")
                        if milestones:
                            st.write("**Milestones:**")
                            for idx, milestone_item in enumerate(milestones, 1):
                                st.write(f"{idx}. {milestone_item}")
                else:
                    st.write(block)

        st.subheader("Projects")
        projects_text = display_as_text(roadmap.get("projects", []))
        st.markdown(projects_text)

        st.subheader("Tools & Technologies")
        tools = roadmap.get("tools_and_tech", [])
        if tools:
            for idx, tool in enumerate(tools, 1):
                st.write(f"{idx}. {tool}")

        st.subheader("Motivation & Tips")
        motivation = roadmap.get("motivation_and_tips", [])
        if motivation:
            for idx, tip in enumerate(motivation, 1):
                st.write(f"{idx}. {tip}")

        with st.expander("Raw JSON Output"):
            st.json(roadmap)

