from typing import Dict, Any, Tuple, List
import spacy
from spacy.matcher import Matcher

nlp = spacy.load("en_core_web_md")

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

    for ent in doc.ents:
        if ent.label_ == "DATE":
            if not entities["time_period"]["start"]:
                entities["time_period"]["start"] = ent.text
            else:
                entities["time_period"]["end"] = ent.text
    
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

def analyze_query_intent(text: str) -> Dict[str, Any]:
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
