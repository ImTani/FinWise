import os
import streamlit as st
from neo4j import GraphDatabase
import openai
from datetime import datetime
from modules.database_manager import DatabaseManager
from modules.conversation_manager import Conversation, ConversationContext, save_conversation, load_conversation
from modules.nlp_processor import extract_entities_and_intent, extract_time_period, analyze_query_intent
from modules.query_generator import QueryGenerator
from modules.chatbot import chatbot_with_context
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

def create_driver(uri, username, password):
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        return driver
    except Exception as e:
        logger.error(f"Error creating driver: {e}")
        return None

def process_user_input(user_input: str, context: ConversationContext, db_manager: DatabaseManager) -> str:
    entities, intent = extract_entities_and_intent(user_input)
    time_period = extract_time_period(user_input)
    query_intent = analyze_query_intent(user_input)
    
    query = QueryGenerator.generate_query(query_intent, context.current_entities)
    kg_response = db_manager.execute_query(query)
    
    if not kg_response:
        kg_response = db_manager.get_all_data()
    
    context.update(user_input, entities["companies"], entities["metrics"], time_period, query_intent, str(kg_response))
    
    ai_response = chatbot_with_context(user_input, context, client, GAIA_NODE_NAME)
    context.update_ai_response(ai_response)
    return ai_response

def generate_insight(db_manager: DatabaseManager) -> str:
    prompt = "Fetch the latest data from our database and return a meaningul, bite-sized, and concise insight about the data. Return as short and concise a message as possible."

    insight = process_user_input(prompt, ConversationContext(), db_manager)

    return insight

def main():
    st.set_page_config(page_title="FinWise AI", page_icon="💼", layout="wide", initial_sidebar_state="expanded")

    if 'current_conversation' not in st.session_state:
        st.session_state.current_conversation = Conversation()

    if 'conversations' not in st.session_state:
        st.session_state.conversations = {}

    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager(driver)
        if st.session_state.db_manager.database_is_empty():
            st.error("The database is empty. Please add some data before using FinWise AI.")

    # Sidebar
    with st.sidebar:
        st.title("FinWise AI")

        if st.button("🔄 New Conversation"):
            st.session_state.conversations = save_conversation(st.session_state.current_conversation, st.session_state.conversations)
            st.session_state.current_conversation = Conversation()  # New conversation is created without a title.
            st.rerun()

        st.subheader("Past Conversations")
        conversations = list(st.session_state.conversations.values())
        conversations.sort(key=lambda x: datetime.fromisoformat(x['updated_at']), reverse=True)

        for conv in conversations[:10]:  # Show only the 10 most recent conversations
            conv_id = conv['id']
            conv_title = conv['title'][:10] + "..." 

            cols = st.columns([5, 1])
            if cols[0].button(conv_title, key=f"conv_{conv_id}"):
                st.session_state.current_conversation = load_conversation(conv_id, st.session_state.conversations)
                st.rerun()

            # Rename button logic
            if cols[1].button("✏️", key=f"rename_btn_{conv_id}", help="Rename"):
                new_title = st.text_input(f"Rename {conv_title}:", value=conv['title'], key=f"rename_input_{conv_id}")

                # Submit button for renaming
                if st.button("Submit", key=f"submit_rename_{conv_id}"):
                    if new_title != conv['title'] and new_title.strip():
                        conv['title'] = new_title.strip()  # Strip whitespace
                        st.session_state.conversations = save_conversation(Conversation.from_dict(conv), st.session_state.conversations)
                        st.rerun()

        if len(conversations) > 10:
            with st.expander("Show more"):
                for conv in conversations[10:]:
                    if st.button(f"{conv['title'][:10]}...", key=f"conv_{conv['id']}"):
                        st.session_state.current_conversation = load_conversation(conv['id'], st.session_state.conversations)
                        st.rerun()

        with st.divider():
            pass

        with st.expander("📊 Database", expanded=False):
            # Input fields for Neo4j connection
            new_uri = st.text_input("Neo4j Connection URI", value=AURA_CONNECTION_URI)
            new_username = st.text_input("Username", value=AURA_USERNAME)
            new_password = st.text_input("Password", value=AURA_PASSWORD, type="password")

            if st.button("Load Database"):
                try:
                    new_driver = create_driver(new_uri, new_username, new_password)
                    if new_driver is not None:
                        st.session_state.db_manager = DatabaseManager(new_driver)
                        stats = st.session_state.db_manager.get_database_stats()
                        st.success("Database loaded successfully.")
                        st.write(f"Companies: {stats['companies']}")
                        st.write(f"Metrics: {stats['metrics']}")
                        st.write(f"Metric Values: {stats['metric_values']}")
                    else:
                        st.error("Failed to connect to the database. Please check your credentials.")
                except Exception as e:
                    st.error(f"Error loading database: {e}")

        with st.expander("ℹ️ Help / About", expanded=False):
            st.write("FinWise AI is your advanced financial assistant. Ask questions about companies, financial metrics, and market trends to get insightful answers backed by our comprehensive database.")

    # Main chat area
    st.header(st.session_state.current_conversation.title)

    # Display chat messages
    for msg in st.session_state.current_conversation.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # User input
    user_input = st.chat_input("Type your message here...")
    if user_input:
        st.session_state.current_conversation.add_message("user", user_input)
        
        with st.chat_message("user"):
            st.write(user_input)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = process_user_input(user_input, st.session_state.current_conversation.context, st.session_state.db_manager)
            st.write(response)
        
        st.session_state.current_conversation.add_message("assistant", response)
        st.session_state.conversations = save_conversation(st.session_state.current_conversation, st.session_state.conversations)

    # Recent Insights
    with st.sidebar:
        st.subheader("Recent Insights")
        st.info(generate_insight(db_manager=st.session_state.db_manager))

if __name__ == "__main__":
    main()