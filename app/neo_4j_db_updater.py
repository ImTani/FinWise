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
        ("Apple", "Technology", "United States", 365000, 147000),
        ("Microsoft", "Technology", "United States", 198000, 221000)
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
        # Create Companies
        for company, industry, location, revenue, employees in companies:
            logging.info(f"Adding company: {company}")
            session.execute_write(create_company, company, industry, location, revenue, employees)
        
        # Define the date range for 5 years
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*5)  # 5 years of data
        current_date = start_date
        
        logging.info("Adding metric values and reports.")
        while current_date <= end_date:
            for company, _, _, _, _ in companies:
                for metric, _, unit in metrics:
                    # Generate realistic sample values based on metric
                    if metric == "Revenue":
                        if company == "Apple":
                            value = random.uniform(200, 400) * 1000  # USD Millions
                        elif company == "Microsoft":
                            value = random.uniform(150, 250) * 1000  # USD Millions
                        else:
                            value = random.uniform(50, 2000)
                    elif metric == "Net Profit":
                        if company == "Apple":
                            value = random.uniform(50, 100) * 1000
                        elif company == "Microsoft":
                            value = random.uniform(40, 90) * 1000
                        else:
                            value = random.uniform(0, 2000)
                    elif metric == "EBITDA":
                        if company == "Apple":
                            value = random.uniform(70, 120) * 1000
                        elif company == "Microsoft":
                            value = random.uniform(60, 110) * 1000
                        else:
                            value = random.uniform(0, 2000)
                    elif metric == "EPS":
                        if company == "Apple":
                            value = random.uniform(3, 6)
                        elif company == "Microsoft":
                            value = random.uniform(5, 9)
                        else:
                            value = random.uniform(0.1, 100)
                    elif metric == "Debt to Equity":
                        if company == "Apple":
                            value = random.uniform(1.0, 2.0)
                        elif company == "Microsoft":
                            value = random.uniform(0.5, 1.5)
                        else:
                            value = random.uniform(0.1, 5.0)
                    elif metric == "Employee Count":
                        value = random.randint(1000, 200000)
                    else:
                        value = random.uniform(0.1, 5.0)
                    
                    # Adjust units for Apple and Microsoft metrics
                    if company in ["Apple", "Microsoft"] and metric in ["Revenue", "Net Profit", "EBITDA"]:
                        # Assuming values are in USD Millions
                        pass  # Values already set appropriately
                    elif metric == "Employee Count":
                        pass  # No change needed
                    else:
                        # For other companies, you might need to adjust units if necessary
                        pass
                    
                    # Add metric value
                    session.execute_write(add_metric_value, company, metric, round(value, 2), current_date.strftime("%Y-%m-%d"))
            
            current_date += timedelta(days=90)  # Quarterly data
        
        report_types = ["Annual", "Quarterly"]
        for company, _, _, _, _ in companies:
            for report_type in report_types:
                date = end_date - timedelta(days=random.randint(0, 365*5))
                content = generate_sample_report_content(company, report_type)
                session.execute_write(add_report, company, report_type, date.strftime("%Y-%m-%d"), content)

    logging.info("Database population complete.")

if __name__ == "__main__":
    populate_database()
    driver.close()
