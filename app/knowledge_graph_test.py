import os
from typing import List, Dict, Any, Tuple
from collections import deque
import streamlit as st
import spacy
from spacy.matcher import Matcher
from neo4j import GraphDatabase
import openai
import logging

class DatabaseManager:
    def __init__(self, driver):
        self.driver = driver

    def execute_query(self, query: str, params: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        try:
            with self.driver.session() as session:
                result = session.run(query, params)
                return result.data()
        except Exception as e:
            logger.error(f"Neo4j query failed: {e}")
            return []

    def clear_database(self):
        query = "MATCH (n) DETACH DELETE n"
        self.execute_query(query)

    def add_company(self, company_name: str):
        query = "CREATE (c:Company {name: $name})"
        self.execute_query(query, {"name": company_name})

    def add_metric(self, company_name: str, metric_name: str, value: Any):
        query = """
        MATCH (c:Company {name: $company_name})
        CREATE (m:Metric {name: $metric_name, value: $value})
        CREATE (c)-[:HAS_METRIC]->(m)
        """
        self.execute_query(query, {"company_name": company_name, "metric_name": metric_name, "value": value})

    def add_document(self, company_name: str, document_type: str, content: str):
        query = """
        MATCH (c:Company {name: $company_name})
        CREATE (d:Document {type: $document_type, content: $content})
        CREATE (c)-[:HAS_DOCUMENT]->(d)
        """
        self.execute_query(query, {"company_name": company_name, "document_type": document_type, "content": content})

class QueryGenerator:
    @staticmethod
    def generate_query(intent: Dict[str, Any], entities: Dict[str, Any]) -> str:
        if intent["action"] == "compare":
            return QueryGenerator._generate_comparison_query(entities)
        elif intent["action"] == "trend":
            return QueryGenerator._generate_trend_query(entities)
        else:
            return QueryGenerator._generate_display_query(entities)

    @staticmethod
    def _generate_comparison_query(entities: Dict[str, Any]) -> str:
        companies = entities["companies"]
        metrics = entities["metrics"]
        time_period = entities["time_period"]

        query = f"""
        MATCH (c:Company)-[:HAS_METRIC]->(m:Metric)
        WHERE c.name IN {companies} AND m.name IN {metrics}
        RETURN c.name AS company, m.name AS metric, m.value AS value
        """
        return query

    @staticmethod
    def _generate_trend_query(entities: Dict[str, Any]) -> str:
        companies = entities["companies"]
        metrics = entities["metrics"]
        time_period = entities["time_period"]

        query = f"""
        MATCH (c:Company)-[:HAS_METRIC]->(m:Metric)
        WHERE c.name IN {companies} AND m.name IN {metrics}
        RETURN c.name AS company, m.name AS metric, m.value AS value
        ORDER BY m.timestamp
        """
        return query

    @staticmethod
    def _generate_display_query(entities: Dict[str, Any]) -> str:
        companies = entities["companies"]
        metrics = entities["metrics"]
        time_period = entities["time_period"]

        query = f"""
        MATCH (c:Company)-[:HAS_METRIC]->(m:Metric)
        WHERE c.name IN {companies} AND m.name IN {metrics}
        RETURN c.name AS company, m.name AS metric, m.value AS value
        """
        return query

class ConversationContext:
    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.history = deque(maxlen=max_history)
        self.current_entities = {
            "companies": [],
            "metrics": [],
            "time_period": "latest"
        }
        self.current_intent = {}
        self.kg_data = ""
        self.last_ai_response = ""

    def update(self, user_input: str, companies: List[str], metrics: List[str], 
               time_period: str, intent: Dict[str, Any], kg_response: str):
        self.current_entities["companies"] = companies if companies else self.current_entities["companies"]
        self.current_entities["metrics"] = metrics if metrics else self.current_entities["metrics"]
        self.current_entities["time_period"] = time_period if time_period != "latest" else self.current_entities["time_period"]
        self.current_intent = intent
        self.kg_data = kg_response

        self.history.append({
            "user_input": user_input,
            "entities": self.current_entities.copy(),
            "intent": self.current_intent.copy(),
            "kg_data": self.kg_data,
            "ai_response": self.last_ai_response
        })

    def update_ai_response(self, ai_response: str):
        self.last_ai_response = ai_response
        if self.history:
            self.history[-1]["ai_response"] = ai_response

    def get_context_summary(self) -> Dict[str, Any]:
        return {
            "current_entities": self.current_entities,
            "current_intent": self.current_intent,
            "recent_history": list(self.history),
            "kg_data": self.kg_data,
            "last_ai_response": self.last_ai_response
        }


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

# Load NLP model
nlp = spacy.load("en_core_web_md")

# Neo4j driver
driver = GraphDatabase.driver(AURA_CONNECTION_URI, auth=(AURA_USERNAME, AURA_PASSWORD))

# OpenAI client
client = openai.OpenAI(base_url=GAIA_NODE_URL, api_key=GAIA_NODE_API_KEY)

def extract_entities_and_intent(text: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    doc = nlp(text)
    
    entities = {
        "companies": [],
        "metrics": [],
        "time_period": {"start": None, "end": None},
        "industry": None
    }
    
    intent = {
        "action": "unknown",
        "comparison": False,
        "trend": False
    }
    
    entities["companies"] = [ent.text for ent in doc.ents if ent.label_ in ["ORG", "PRODUCT"]]
    
    matcher = Matcher(nlp.vocab)
    financial_patterns = [
        [{"LOWER": {"IN": ["revenue", "profit", "income", "earnings", "ebitda", "sales"]}},
         {"POS": "ADP", "OP": "?"},
         {"POS": "NUM", "OP": "?"}],
        [{"LOWER": "net"}, {"LOWER": {"IN": ["income", "profit", "loss"]}}],
        [{"LOWER": "gross"}, {"LOWER": "margin"}],
        [{"LOWER": "operating"}, {"LOWER": {"IN": ["income", "profit", "margin"]}}]
    ]
    matcher.add("FINANCIAL_METRIC", financial_patterns)
    matches = matcher(doc)
    entities["metrics"] = [doc[start:end].text for _, start, end in matches]

    # Extract time period
    for ent in doc.ents:
        if ent.label_ == "DATE":
            if not entities["time_period"]["start"]:
                entities["time_period"]["start"] = ent.text
            else:
                entities["time_period"]["end"] = ent.text
    
    # Extract industry
    industries = ["IT Services", "Conglomerate", "Banking", "Telecommunications"]
    for token in doc:
        if token.text in industries:
            entities["industry"] = token.text
            break
    
    return entities, intent

def extract_time_period(text: str) -> str:
    doc = nlp(text)
    time_entities = [ent.text for ent in doc.ents if ent.label_ in ["DATE", "TIME"]]
    if time_entities:
        return time_entities[0]
    return "latest"

def analyze_query_intent(text: str) -> Dict[str, str]:
    doc = nlp(text)
    intent = {
        "action": "unknown",
        "comparison": False,
        "trend": False
    }
    
    if any(token.lemma_ in ["compare", "versus", "vs"] for token in doc):
        intent["action"] = "compare"
        intent["comparison"] = True
    elif any(token.lemma_ in ["trend", "change", "grow", "decline"] for token in doc):
        intent["action"] = "trend"
        intent["trend"] = True
    elif any(token.lemma_ in ["show", "display", "give", "provide"] for token in doc):
        intent["action"] = "display"
    
    return intent

def safe_neo4j_query(query: str, params: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
    try:
        with driver.session() as session:
            result = session.run(query, params)
            return result.data()
    except Exception as e:
        logger.error(f"Neo4j query failed: {e}")
        return []

def get_company_metrics(company_name: str) -> List[Dict[str, Any]]:
    query = """
    MATCH (c:Company {name: $company_name})-[:HAS_METRIC]->(m:Metric)
    RETURN m.name AS metric, m.value AS value
    """
    return safe_neo4j_query(query, {"company_name": company_name})

def generate_system_message() -> str:
    return """You are FinWise, an advanced financial assistant with access to a knowledge graph containing company metrics and reports. Your primary role is to provide accurate, concise, and helpful financial information and insights. Follow these guidelines:

1. Use the provided database query results to answer questions about companies, their metrics, and reports.
2. If the database lacks data, provide a general response based on your financial knowledge.
3. Always specify the source of your information (database or general knowledge).
4. Use the Indian numeric system and Indian Rupee for all financial values.
5. If comparing companies or metrics, clearly state the basis of comparison.
6. For trend analysis, provide a brief explanation of factors influencing the trend.
7. If asked about future predictions, clearly state that these are estimates based on current data and trends.
8. When referencing reports, summarize key points but encourage users to read the full report for detailed information.

You have access to the following database queries:
1. get_company_metrics(company, metric, start_date, end_date)
2. get_company_reports(company, report_type)
3. get_companies_by_industry(industry)

Use these queries to fetch relevant data before responding to the user."""

def prepare_messages(system_message: str, user_input: str, context: ConversationContext) -> List[Dict[str, str]]:
    context_summary = context.get_context_summary()
    
    context_string = f"""
    Current Entities: {context_summary['current_entities']}
    Current Intent: {context_summary['current_intent']}
    Knowledge Graph Data: {context_summary['kg_data']}
    
    Recent Conversation History:
    {' '.join([f"User: {item['user_input']}\nAI: {item['ai_response']}" for item in context_summary['recent_history']])}
    """
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": f"Context: {context_string}\n\nUser Query: {user_input}"}
    ]
    return messages

def process_user_input(user_input: str, context: ConversationContext, db_manager: DatabaseManager) -> str:
    companies, metrics = extract_entities_and_metrics(user_input)
    time_period = extract_time_period(user_input)
    query_intent = analyze_query_intent(user_input)
    
    # Check if the user wants to modify the database
    if "update database" in user_input.lower() or "modify database" in user_input.lower():
        return handle_database_modification(user_input, db_manager)
    
    # Generate and execute dynamic query
    query = QueryGenerator.generate_query(query_intent, context.current_entities)
    kg_response = db_manager.execute_query(query)
    
    context.update(user_input, companies, metrics, time_period, query_intent, str(kg_response))
    
    ai_response = chatbot_with_context(user_input, context)
    context.update_ai_response(ai_response)
    return ai_response

def handle_database_modification(user_input: str, db_manager: DatabaseManager) -> str:
    # Generate a plan for database modification
    plan = generate_db_modification_plan(user_input)
    
    # Ask for user confirmation
    confirmation = st.button(f"Confirm the following changes:\n{plan}")
    
    if confirmation:
        # Execute the plan
        execute_db_modification_plan(plan, db_manager)
        return "Database has been updated according to your instructions."
    else:
        return "No changes were made to the database. Please confirm the changes to proceed."

def generate_db_modification_plan(user_input: str) -> str:
    # Use LLM to generate a plan based on user input
    prompt = f"Generate a step-by-step plan to modify the database based on this request: {user_input}"
    response = client.chat.completions.create(
        model=GAIA_NODE_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=200
    )
    return response.choices[0].message.content

def execute_db_modification_plan(plan: str, db_manager: DatabaseManager):
    # Parse the plan and execute each step
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
        elif step.startswith("Add document"):
            parts = step.split(":")
            company_name = parts[1].strip()
            document_type = parts[2].strip()
            content = parts[3].strip()
            db_manager.add_document(company_name, document_type, content)

def chatbot_with_context(user_input: str, context: ConversationContext) -> str:
    system_message = generate_system_message()
    messages = prepare_messages(system_message, user_input, context)
    
    try:
        completion = client.chat.completions.create(
            model=GAIA_NODE_NAME,
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error in LLM request: {e}")
        return "I apologize, but I encountered an error while processing your request. Please try again."

# Streamlit app
st.title("FinWise AI")

if "context" not in st.session_state:
    st.session_state.context = ConversationContext()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "How can I help you with financial information today?"}]

if "db_manager" not in st.session_state:
    st.session_state.db_manager = DatabaseManager(driver)

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    response = process_user_input(prompt, st.session_state.context, st.session_state.db_manager)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.chat_message("assistant").write(response)

# Sidebar
with st.sidebar:
    st.header("About FinWise AI")
    st.write("FinWise AI is your advanced financial assistant, providing insights and information about companies and their financial metrics.")
    st.write("Ask about company revenues, profits, compare metrics, or inquire about financial trends!")