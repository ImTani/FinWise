from os import environ
from neo4j import GraphDatabase
import openai
import streamlit as st

AURA_CONNECTION_URI: str = "neo4j+s://2df8ccfd.databases.neo4j.io:7687"
AURA_USERNAME: str = "neo4j"
AURA_PASSWORD: str = environ.get("NEO4J_PASSWORD")

GAIA_NODE_URL: str = "https://gemma.us.gaianet.network/v1"
GAIA_NODE_NAME: str = "gemma"
GAIA_NODE_API_KEY: str = "API_KEY"

# Driver instantiation
driver = GraphDatabase.driver(
    AURA_CONNECTION_URI,
    auth=(AURA_USERNAME, AURA_PASSWORD)
)

client = openai.OpenAI(base_url=GAIA_NODE_URL, api_key=GAIA_NODE_API_KEY)

def chatbot(user_input) -> str:
    completion = client.chat.completions.create(
        model=GAIA_NODE_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are a financial assistant that prioritizes data from a knowledge graph. Always use the information from the graph when available to answer questions about companies and metrics. If the graph lacks the data, provide a general response based on your broader knowledge."},
            
            {
                "role": "user",
                "content": user_input
            }
        ]
    )

    return completion.choices[0].message.content

def add_company_to_neo4j(driver, company_name):
    with driver.session() as session:
        session.run(
            "CREATE (c:Company {name: $name}) RETURN c",
            name=company_name
        )

def add_metric_to_neo4j(driver, company_name, metric_name, value):
    with driver.session() as session:
        session.run(
            """
            MATCH (c:Company {name: $company_name})
            CREATE (m:Metric {name: $metric_name, value: $value})
            CREATE (c)-[:HAS_METRIC]->(m)
            RETURN m
            """,
            company_name=company_name,
            metric_name=metric_name,
            value=value
        )

def query_neo4j(driver, query):
    with driver.session() as session:
        result = session.run(query)
        return result.data()

def get_company_metrics(driver, company_name):
    query = f"""
    MATCH (c:Company {{name: '{company_name}'}})-[:HAS_METRIC]->(m:Metric)
    RETURN m.name AS metric, m.value AS value
    """
    result = query_neo4j(driver, query)
    return result

def extract_company_from_input(user_input):
    """
    This function extracts a company name from user input.
    You can improve it with NLP techniques to better capture companies.
    """
    # Simplified for demo purposes: Could be replaced with more robust NLP extraction
    companies = ["Acme Corp", "Globex Inc", "Initech", "Umbrella Corp", "Soylent Corp", "Wayne Enterprises", "Stark Industries"]
    result = []
    for company in companies:
        if company in user_input:
            result.append(company)

    if len(result) > 0:
        return result
    else:
        return None

def chatbot_with_kg(user_input):
    # Try to extract the company name from the user input
    company_names = extract_company_from_input(user_input)
    kg_response: str = ""

    for company_name in company_names:
        if company_name:  # If a company is mentioned in the input
            metrics = get_company_metrics(driver, company_name)
            
            if metrics:
                metrics_text = ", ".join([f"{m['metric']}: {m['value']}" for m in metrics])
                kg_response += f"The metrics for {company_name} are: {metrics_text}.\n"
            else:
                kg_response += f"No metrics found for {company_name}.\n"
            
    # Use the LLM to provide a natural language response with the KG data
    final_prompt = f"User Query: {user_input}, Stored Data: {kg_response}"
    print(f"User Query: {user_input}, Stored Data: {kg_response}, LLM Prompt: {final_prompt}")
    response = chatbot(final_prompt)
    
    return response

# Example usage
user_input = "How is Wayne Enterprises doing today?"
response = chatbot_with_kg(user_input)
print(response)

with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
    "[View the source code](https://github.com/streamlit/llm-examples/blob/main/Chatbot.py)"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"

st.title("FinWise AI")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "Financial Assitant", "content": "How can I help you?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    response = chatbot_with_kg(prompt)
    msg = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": msg})
    st.chat_message("assistant").write(msg)