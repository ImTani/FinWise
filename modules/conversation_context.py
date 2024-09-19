from typing import Dict, Any, List
from collections import deque

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
