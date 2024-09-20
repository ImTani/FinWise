import logging
from neo4j import GraphDatabase
import random
from datetime import datetime, timedelta

# Logging setup for your application
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Set Neo4j driver log level to WARNING or ERROR to suppress excessive debug output from Neo4j internals
logging.getLogger("neo4j").setLevel(logging.WARNING)  # You can also set it to ERROR if you want only error logs

# Neo4j connection (update with your actual credentials)
URI = "neo4j+s://2df8ccfd.databases.neo4j.io:7687"
AUTH = ("neo4j", "m0bp___En5qsHdQyjxKEuxCx-lMEZBgmgNESxLjZIHw")

driver = GraphDatabase.driver(URI, auth=AUTH)

def clear_database():
    logging.info("Clearing the database.")
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    logging.info("Database cleared.")

def create_constraints():
    logging.info("Creating constraints.")
    with driver.session() as session:
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Metric) REQUIRE m.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Report) REQUIRE r.id IS UNIQUE")
    logging.info("Constraints created.")

def create_company(tx, name, industry, location, revenue, employees):
    logging.debug(f"Creating company: {name}")
    tx.run("""
    CREATE (:Company {
        name: $name, 
        industry: $industry, 
        location: $location, 
        revenue: $revenue, 
        employees: $employees
    })""", name=name, industry=industry, location=location, revenue=revenue, employees=employees)

def create_metric(tx, name, description, unit):
    logging.debug(f"Creating metric: {name}")
    tx.run("""
    CREATE (:Metric {
        name: $name, 
        description: $description, 
        unit: $unit
    })""", name=name, description=description, unit=unit)

def add_metric_value(tx, company, metric, value, date):
    logging.debug(f"Adding metric value for {company}: {metric} = {value} on {date}")
    tx.run("""
    MATCH (c:Company {name: $company}), (m:Metric {name: $metric})
    CREATE (c)-[:HAS_METRIC]->(m)
    CREATE (m)-[:HAS_VALUE]->(mv:MetricValue {value: $value, date: $date})-[:OF_METRIC]->(m)
    """, company=company, metric=metric, value=value, date=date)

def add_report(tx, company, report_type, date, content):
    logging.debug(f"Adding {report_type} report for {company} on {date}")
    tx.run("""
    MATCH (c:Company {name: $company})
    CREATE (c)-[:HAS_REPORT]->(r:Report {id: $id, type: $type, date: $date, content: $content})
    """, company=company, id=f"{company}_{report_type}_{date}", type=report_type, date=date, content=content)

def generate_sample_report_content(company, report_type):
    financial_overview = f"{company} saw substantial changes in the {report_type.lower()} period. Highlights include revenue growth driven by key business segments and strong market positioning."
    challenges = "Challenges faced include fluctuations in commodity prices and regulatory changes in key markets."
    future_outlook = "The company expects continued growth through digital transformation initiatives and expansion into new markets."
    return f"Financial Overview: {financial_overview}\nChallenges: {challenges}\nFuture Outlook: {future_outlook}"

def populate_database():
    logging.info("Starting database population.")
    
    companies = [
        ("TCS", "IT Services", "India", 18000, 100000),
        ("Infosys", "IT Services", "India", 12000, 85000),
        ("Reliance Industries", "Conglomerate", "India", 50000, 150000),
        ("HDFC Bank", "Banking", "India", 20000, 80000),
        ("Bharti Airtel", "Telecommunications", "India", 16000, 120000)
    ]
    
    metrics = [
        ("Revenue", "Total revenue earned", "INR Crores"),
        ("Net Profit", "Profit after tax", "INR Crores"),
        ("EBITDA", "Earnings Before Interest, Taxes, Depreciation, and Amortization", "INR Crores"),
        ("EPS", "Earnings Per Share", "INR per Share"),
        ("Debt to Equity", "Ratio of total liabilities to shareholders' equity", "Ratio"),
        ("Employee Count", "Total number of employees", "Number")
    ]
    
    with driver.session() as session:
        for company, industry, location, revenue, employees in companies:
            logging.info(f"Adding company: {company}")
            session.execute_write(create_company, company, industry, location, revenue, employees)
        
        for metric, description, unit in metrics:
            logging.info(f"Adding metric: {metric}")
            session.execute_write(create_metric, metric, description, unit)
        
        # Add sample metric values
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*3)  # 3 years of data
        current_date = start_date
        
        logging.info("Adding metric values and reports.")
        while current_date <= end_date:
            for company, _, _, _, _ in companies:
                for metric, _, _ in metrics:
                    if metric in ["Revenue", "EBITDA", "Net Profit"]:
                        value = random.uniform(50, 2000)
                    elif metric == "EPS":
                        value = random.uniform(5, 100)
                    elif metric == "Employee Count":
                        value = random.randint(1000, 200000)
                    else:
                        value = random.uniform(0.1, 5.0)
                    session.execute_write(add_metric_value, company, metric, round(value, 2), current_date.strftime("%Y-%m-%d"))
            
            current_date += timedelta(days=90)  # Quarterly data
        
        report_types = ["Annual", "Quarterly"]
        for company, _, _, _, _ in companies:
            for report_type in report_types:
                date = end_date - timedelta(days=random.randint(0, 365))
                content = generate_sample_report_content(company, report_type)
                session.execute_write(add_report, company, report_type, date.strftime("%Y-%m-%d"), content)

    logging.info("Database population complete.")

if __name__ == "__main__":
    clear_database()
    create_constraints()
    populate_database()
    driver.close()
