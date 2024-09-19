from os import environ
from neo4j import GraphDatabase
import openai
import streamlit as st
import spacy

AURA_CONNECTION_URI: str = "neo4j+s://2df8ccfd.databases.neo4j.io:7687"
AURA_USERNAME: str = "neo4j"
AURA_PASSWORD: str = environ.get("NEO4J_PASSWORD") or "m0bp___En5qsHdQyjxKEuxCx-lMEZBgmgNESxLjZIHw"

GAIA_NODE_URL: str = "https://llama.us.gaianet.network/v1"
GAIA_NODE_NAME: str = "llama"
GAIA_NODE_API_KEY: str = "API_KEY"

nlp = spacy.load("en_core_web_sm")

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
    fixed_query = clean_query_via_llm(query)

    with driver.session() as session:
        result = session.run(fixed_query)
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
    Extracts company names from the user input using NLP (Named Entity Recognition).
    """
    doc = nlp(user_input)
    companies = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    return companies

def extract_metric_from_input(user_input):
    """
    Extracts financial metrics like revenue, profit, etc., using NLP.
    """
    # Customize to recognize specific financial terms (if not already recognized by spaCy)
    financial_terms = ["revenue", "profit", "net income", "earnings", "loss", "EBITDA"]
    extracted_terms = [term for term in financial_terms if term.lower() in user_input.lower()]
    return extracted_terms

def clean_list_via_llm(list_type, items):
    """
    This function takes a list of company names or metrics, 
    and cleans it via LLM (removes duplicates and ensures consistency).
    """
    prompt = f"Clean up the following {list_type} list to be consistent, valid, and unique. Only return the cleaned list:\n{items}"
    response = chatbot(prompt)
    
    # Assuming the response is a valid Python list
    try:
        cleaned_items = eval(response)
        if isinstance(cleaned_items, list):
            return cleaned_items
    except Exception as e:
        print(f"Error cleaning {list_type} list: {e}")
    
    # Return the original list if the LLM fails
    return items

def clean_query_via_llm(query):
    """
    This function takes a potentially incorrect Neo4j query, checks it via the LLM,
    and returns a syntactically correct query. If the query is valid, it is returned as is.
    """
    prompt = f"Review the following Neo4j query for any syntax errors. If there are any issues, fix the query. You should return only the query as your output, and nothing else. Return the same query if it is syntaxically correct. Do not think of suggestions, only check for syntax errors in the given query :\n{query}"
    response = chatbot(prompt)
    
    # Assuming the LLM will return the fixed query as a string
    if response.strip():
        return response.strip()
    
    # Return the original query if there's no meaningful response
    return query

def chatbot_with_kg(user_input):
    # Extract company names and financial metrics from the user input using NLP
    
    company_names = extract_company_from_input(user_input)
    metrics = extract_metric_from_input(user_input)

    print(f"//Original// Company Names: {company_names}\nMetrics: {metrics}")

    # Clean up the lists using the LLM
    company_names = clean_list_via_llm("company names", company_names)
    metrics = clean_list_via_llm("metrics", metrics)
    
    print(f"//Changed// Company Names: {company_names}\nMetrics: {metrics}")


    kg_response = ""
    
    # Loop through the cleaned company names and fetch the metrics from the knowledge graph
    for company_name in company_names:
        if company_name:  # If a company is mentioned in the input
            company_metrics = get_company_metrics(driver, company_name)
            
            if company_metrics:
                # Filter results by requested metrics (if any were specified)
                if metrics:
                    filtered_metrics = [m for m in company_metrics if any(metric in m['metric'].lower() for metric in metrics)]
                    if not filtered_metrics:
                        kg_response += f"No matching metrics found for {company_name}.\n"
                    else:
                        metrics_text = ", ".join([f"{m['metric']}: {m['value']}" for m in filtered_metrics])
                        kg_response += f"The metrics for {company_name} are: {metrics_text}.\n"
                else:
                    # If no specific metric was requested, return all metrics
                    metrics_text = ", ".join([f"{m['metric']}: {m['value']}" for m in company_metrics])
                    kg_response += f"The metrics for {company_name} are: {metrics_text}.\n"
            else:
                kg_response += f"No metrics found for {company_name}.\n"
    
    # If no company names were extracted, prompt the user to provide one
    if not company_names:
        return "Please specify a company to retrieve financial metrics."

    # Use the LLM to generate a natural language response with the KG data
    final_prompt = f"Query: {user_input}\nStored Data: {kg_response}"
    
    response = chatbot(final_prompt)
    
    return response


with st.sidebar:
    "Test Sidebar Item"

st.title("FinWise AI")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "You are a financial assistant that prioritizes data from a knowledge graph. Use the knowledge graph for company metrics whenever available, and provide clear, concise responses. If no relevant data is found, rely on general financial knowledge. Use the Indian numeric system for values and the Indian Rupee as the currency for all queries.", "content": "How can I help you?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    
    # Update conversation with KG and NLP-based extractions
    messages = st.session_state.messages
    full_prompt = f"Conversation so far: {messages}"
    response = chatbot_with_kg(full_prompt)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.chat_message("assistant").write(response)