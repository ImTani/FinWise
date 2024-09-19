from neo4j import GraphDatabase
import random
from datetime import datetime, timedelta

# Neo4j connection (update with your actual credentials)
URI = "neo4j+s://2df8ccfd.databases.neo4j.io:7687"
AUTH = ("neo4j", "m0bp___En5qsHdQyjxKEuxCx-lMEZBgmgNESxLjZIHw")

driver = GraphDatabase.driver(URI, auth=AUTH)

def clear_database():
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

def create_constraints():
    with driver.session() as session:
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Metric) REQUIRE m.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Report) REQUIRE r.id IS UNIQUE")

def create_company(tx, name, industry):
    tx.run("CREATE (:Company {name: $name, industry: $industry})", name=name, industry=industry)

def create_metric(tx, name, description):
    tx.run("CREATE (:Metric {name: $name, description: $description})", name=name, description=description)

def add_metric_value(tx, company, metric, value, date):
    tx.run("""
    MATCH (c:Company {name: $company}), (m:Metric {name: $metric})
    CREATE (c)-[:HAS_METRIC]->(mv:MetricValue {value: $value, date: $date})-[:OF_METRIC]->(m)
    """, company=company, metric=metric, value=value, date=date)

def add_report(tx, company, report_type, date, content):
    tx.run("""
    MATCH (c:Company {name: $company})
    CREATE (c)-[:HAS_REPORT]->(r:Report {id: $id, type: $type, date: $date, content: $content})
    """, company=company, id=f"{company}_{report_type}_{date}", type=report_type, date=date, content=content)

def populate_database():
    companies = [
        ("TCS", "IT Services"),
        ("Infosys", "IT Services"),
        ("Reliance Industries", "Conglomerate"),
        ("HDFC Bank", "Banking"),
        ("Bharti Airtel", "Telecommunications")
    ]
    
    metrics = [
        ("Revenue", "Total revenue earned"),
        ("Net Profit", "Profit after tax"),
        ("EBITDA", "Earnings Before Interest, Taxes, Depreciation, and Amortization"),
        ("EPS", "Earnings Per Share"),
        ("Debt to Equity", "Ratio of total liabilities to shareholders' equity")
    ]
    
    with driver.session() as session:
        for company, industry in companies:
            session.execute_write(create_company, company, industry)
        
        for metric, description in metrics:
            session.execute_write(create_metric, metric, description)
        
        # Add sample metric values
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*3)  # 3 years of data
        current_date = start_date
        
        while current_date <= end_date:
            for company, _ in companies:
                for metric, _ in metrics:
                    value = random.uniform(100, 10000) if metric != "EPS" else random.uniform(1, 100)
                    session.execute_write(add_metric_value, company, metric, round(value, 2), current_date.strftime("%Y-%m-%d"))
            
            current_date += timedelta(days=90)  # Quarterly data
        
        # Add sample reports
        report_types = ["Annual", "Quarterly"]
        for company, _ in companies:
            for report_type in report_types:
                date = end_date - timedelta(days=random.randint(0, 365))
                content = f"This is a sample {report_type.lower()} report for {company}."
                session.execute_write(add_report, company, report_type, date.strftime("%Y-%m-%d"), content)

if __name__ == "__main__":
    clear_database()
    create_constraints()
    populate_database()
    driver.close()