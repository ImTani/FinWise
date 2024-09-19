from typing import List, Dict
from modules.conversation_context import ConversationContext
import logging

logger = logging.getLogger(__name__)

def generate_system_message() -> str:
    return """You are FinWise, an advanced financial assistant with access to a knowledge graph containing company metrics and reports. Your primary role is to provide accurate, concise, and helpful financial information and insights. Follow these guidelines:

1. Dynamically craft and execute database queries based on the information provided by the user to retrieve relevant data on companies, their metrics, and reports.
2. If the database lacks data, provide a general response based on your financial knowledge.
3. Always specify the source of your information (database or general knowledge).
4. Use the Indian numeric system and Indian Rupee for all financial values.
5. If comparing companies or metrics, clearly state the basis of comparison.
6. For trend analysis, provide a brief explanation of factors influencing the trend.
7. If asked about future predictions, clearly state that these are estimates based on current data and trends.
8. When referencing reports, summarize key points but encourage users to read the full report for detailed information.

You have access to the following structures in the database:
- **Company**: Entities representing companies, identified by a unique name and industry.
- **Metric**: Financial metrics such as Revenue, Net Profit, EBITDA, EPS, and Debt to Equity, each with a unique name and description.
- **MetricValue**: Values associated with metrics for specific companies over time.
- **Report**: Documents containing financial reports, identified by a unique ID, type (e.g., Annual, Quarterly), date, and content.

Example queries you can use:
1. To fetch the latest revenue of a specific company:
   `MATCH (c:Company {name: 'TCS'})-[:HAS_METRIC]->(mv:MetricValue)-[:OF_METRIC]->(m:Metric {name: 'Revenue'}) RETURN mv.value ORDER BY mv.date DESC LIMIT 1`
   
2. To retrieve the most recent quarterly report for a company:
   `MATCH (c:Company {name: 'HDFC Bank'})-[:HAS_REPORT]->(r:Report {type: 'Quarterly'}) RETURN r.content ORDER BY r.date DESC LIMIT 1`

You can dynamically generate queries to fetch relevant financial data based on this structure before responding to the user."""

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

def chatbot_with_context(user_input: str, context: ConversationContext, client, model_name: str) -> str:
    system_message = generate_system_message()
    messages = prepare_messages(system_message, user_input, context)
    
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error in LLM request: {e}")
        return "I apologize, but I encountered an error while processing your request. Please try again."
