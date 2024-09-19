import os
import streamlit as st
from neo4j import GraphDatabase
import openai
from modules.database_manager import DatabaseManager
from modules.conversation_context import ConversationContext
from modules.nlp_processor import extract_entities_and_intent, extract_time_period, analyze_query_intent
from modules.query_generator import QueryGenerator
from modules.chatbot import generate_system_message, prepare_messages, chatbot_with_context
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables and configurations
AURA_CONNECTION_URI = os.environ.get("AURA_CONNECTION_URI", "neo4j+s://2df8ccfd.databases.neo4j.io:7687")
AURA_USERNAME = os.environ.get("AURA_USERNAME", "neo4j")
AURA_PASSWORD = os.environ.get("AURA_PASSWORD", "m0bp___En5qsHdQyjxKEuxCx-lMEZBgmgNESxLjZIHw")

GAIA_NODE_URL = os.environ.get("GAIA_NODE_URL", "https://llama.us.gaianet.network/v1")
GAIA_NODE_NAME = os.environ.get("GAIA_NODE_NAME", "llama")
GAIA_NODE_API_KEY = os.environ.get("GAIA_NODE_API_KEY", "API_KEY")

# Neo4j driver
driver = GraphDatabase.driver(AURA_CONNECTION_URI, auth=(AURA_USERNAME, AURA_PASSWORD))

# OpenAI client
client = openai.OpenAI(base_url=GAIA_NODE_URL, api_key=GAIA_NODE_API_KEY)

def process_user_input(user_input: str, context: ConversationContext, db_manager: DatabaseManager) -> str:
    entities, intent = extract_entities_and_intent(user_input)
    time_period = extract_time_period(user_input)
    query_intent = analyze_query_intent(user_input)
    
    if "update database" in user_input.lower() or "modify database" in user_input.lower():
        return handle_database_modification(user_input, db_manager)
    
    query = QueryGenerator.generate_query(query_intent, context.current_entities)
    kg_response = db_manager.execute_query(query)
    
    if not kg_response:
        kg_response = db_manager.get_all_data()
    
    context.update(user_input, entities["companies"], entities["metrics"], time_period, query_intent, str(kg_response))
    
    ai_response = chatbot_with_context(user_input, context, client, GAIA_NODE_NAME)
    context.update_ai_response(ai_response)
    return ai_response

def handle_database_modification(user_input: str, db_manager: DatabaseManager) -> str:
    plan = generate_db_modification_plan(user_input, client, GAIA_NODE_NAME)
    
    confirmation = st.button(f"Confirm the following changes:\n{plan}")
    
    if confirmation:
        execute_db_modification_plan(plan, db_manager)
        return "Database has been updated according to your instructions."
    else:
        return "No changes were made to the database. Please confirm the changes to proceed."

def generate_db_modification_plan(user_input: str, client, model_name):
    prompt = f"Generate a step-by-step plan to modify the database based on this request: {user_input}"
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=200
    )
    return response.choices[0].message.content

def execute_db_modification_plan(plan: str, db_manager: DatabaseManager):
    steps = plan.split("\n")
    for step in steps:
        if step.startswith("Clear database"):
            db_manager.clear_database()
        elif step.startswith("Add company"):
            company_name = step.split(":")[1].strip()
            db_manager.add_company(company_name)
        elif step.startswith("Add metric"):
            parts = step.split(":")
            company_name = parts[1].strip()
            metric_name = parts[2].strip()
            value = parts[3].strip()
            db_manager.add_metric(company_name, metric_name, value)

def main():
    st.title("FinWise AI")

    if "context" not in st.session_state:
        st.session_state.context = ConversationContext()

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "How can I help you with financial information today?"}]

    if "db_manager" not in st.session_state:
        st.session_state.db_manager = DatabaseManager(driver)
        if st.session_state.db_manager.database_is_empty():
            st.session_state.db_manager.populate_sample_data()
            st.success("Database populated with sample data.")

    # Display database stats
    stats = st.session_state.db_manager.get_database_stats()
    st.sidebar.header("Database Stats")
    st.sidebar.write(f"Companies: {stats['companies']}")
    st.sidebar.write(f"Metrics: {stats['metrics']}")
    st.sidebar.write(f"Metric Values: {stats['metric_values']}")

    # Button to reload sample data
    if st.sidebar.button("Reload Sample Data"):
        st.session_state.db_manager.clear_database()
        st.session_state.db_manager.populate_sample_data()
        st.sidebar.success("Sample data reloaded successfully!")

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        response = process_user_input(prompt, st.session_state.context, st.session_state.db_manager)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.chat_message("assistant").write(response)

    with st.sidebar:
        st.header("About FinWise AI")
        st.write("FinWise AI is your advanced financial assistant, providing insights and information about companies and their financial metrics.")
        st.write("Ask about company revenues, profits, compare metrics, or inquire about financial trends!")

if __name__ == "__main__":
    main()