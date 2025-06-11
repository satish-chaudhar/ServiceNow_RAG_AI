import os
import requests
import streamlit as st
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType, Tool
from langchain.llms import OpenAI

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API Key securely
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("❌ OPENAI_API_KEY not found. Please set it in .env file or environment.")
    st.stop()

# Initialize OpenAI LLM
llm = OpenAI(temperature=0.5, openai_api_key=openai_api_key)

# --- ServiceNow API Wrapper ---
class ServiceNowAPIWrapper:
    def __init__(self, instance_url, username, password):
        self.instance_url = instance_url
        self.auth = (username, password)

    def get_incident_status(self, incident_number):
        url = f"{self.instance_url}/api/now/table/incident?sysparm_query=number={incident_number}&sysparm_limit=1"
        headers = {"Accept": "application/json"}
        response = requests.get(url, auth=self.auth, headers=headers)
        if response.status_code == 200:
            result = response.json().get('result', [])
            if result:
                incident = result[0]
                assigned_to = incident.get("assigned_to")
                if isinstance(assigned_to, dict):
                    assigned_to_display = assigned_to.get("display_value", "N/A")
                else:
                    assigned_to_display = assigned_to or "N/A"

                return {
                    "Number": incident.get("number"),
                    "Short Description": incident.get("short_description"),
                    "State": incident.get("state"),
                    "Priority": incident.get("priority"),
                    "Assigned To": assigned_to_display,
                    "Updated": incident.get("sys_updated_on")
                }
            else:
                return {"error": "Incident not found"}
        else:
            return {"error": f"API Error: {response.status_code}"}

# --- Streamlit UI ---
st.title("🔧 ServiceNow Incident Status Chatbot")

# Ask for credentials in sidebar
with st.sidebar:
    st.subheader("🔐 ServiceNow Credentials")
    instance_url = st.text_input("Instance URL", value="https://dev182735.service-now.com")
    username = st.text_input("Username", type="default")
    password = st.text_input("Password", type="password")

# Input field for Incident ID
incident_id = st.text_input("Enter Incident ID (e.g. INC0010001):")

# Only proceed if credentials and ID are provided
if incident_id and instance_url and username and password:
    # Initialize ServiceNow wrapper
    snow_api = ServiceNowAPIWrapper(instance_url, username, password)

    # Tool function for LangChain
    def fetch_status(incident_number: str) -> str:
        result = snow_api.get_incident_status(incident_number)

        if "error" in result:
            return f"❌ {result['error']}"

        return (
            f"📄 Incident: {result['Number']}\n"
            f"📝 Description: {result['Short Description']}\n"
            f"📌 State: {result['State']}\n"
            f"⚠️ Priority: {result['Priority']}\n"
            f"👤 Assigned To: {result['Assigned To'] or 'N/A'}\n"
            f"🕒 Last Updated: {result['Updated']}"
        )

    # Create LangChain tool
    tools = [
        Tool(
            name="ServiceNow Incident Lookup",
            func=fetch_status,
            description="Gets incident status from ServiceNow by incident number"
        )
    ]

    # Initialize LangChain agent
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )

    # Run query through LangChain
    with st.spinner("🔍 Fetching incident status..."):
        try:
            result = agent.run(incident_id)
            st.success("✅ Incident Status:")
            st.write(result)
        except Exception as e:
            st.error("❌ Error while processing request.")
            st.exception(e)
else:
    st.info("ℹ️ Please enter your ServiceNow credentials and an incident ID.")
