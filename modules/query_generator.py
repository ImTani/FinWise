from typing import Dict, Any

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
