# sentiment_model.py - UPDATED VERSION
import re
from transformers import pipeline

class SentimentAnalyzer:
    def __init__(self):
        print("[sentiment] Loading sentiment analyzer...")
        try:
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english"
            )
        except:
            self.sentiment_pipeline = None
            print("[sentiment] Using rule-based sentiment only")
        
        self.support_sentiments = {
            "Angry": [
                "unacceptable", "furious", "terrible", "worst", "angry", 
                "outrage", "infuriating", "horrible", "awful", "disgusting",
                "fuming", "mad", "outraged"
            ],
            "Frustrated": [
                "frustrated", "annoying", "problem", "issue", "stuck", 
                "can't", "doesn't work", "broken", "wrong", "fed up",
                "crashes", "crash", "error", "bug", "fails", "failed",
                "glitch", "not working", "doesn't", "cannot"
            ],
            "Confused": [
                "confused", "unclear", "don't understand", "what does",
                "how to", "why is", "where is", "clueless"
            ],
            "Positive": [
                "thanks", "appreciate", "great", "good", "helpful", 
                "love", "awesome", "excellent", "perfect", "happy",
                "works great", "solved", "fixed"
            ]
        }
    
    def predict_sentiment_with_confidence(self, text):
        if not isinstance(text, str):
            return {"sentiment": "Neutral", "confidence": 0.5}
        
        text_lower = text.lower()
        
        # Check for support-specific sentiments
        for sentiment, keywords in self.support_sentiments.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return {"sentiment": sentiment, "confidence": 0.95}
        
        # Check for urgent/negative markers
        urgent_markers = ["urgent", "asap", "immediately", "right now", "critical"]
        if any(marker in text_lower for marker in urgent_markers):
            if any(word in text_lower for word in ["crash", "error", "broken", "can't"]):
                return {"sentiment": "Frustrated", "confidence": 0.9}
            return {"sentiment": "Angry", "confidence": 0.85}
        
        if self.sentiment_pipeline:
            try:
                result = self.sentiment_pipeline(text[:512])[0]
                if result['label'] == 'POSITIVE' and result['score'] > 0.9:
                    return {"sentiment": "Positive", "confidence": round(float(result["score"]), 3)}
                elif result['label'] == 'NEGATIVE' and result['score'] > 0.8:
                    return {"sentiment": "Frustrated", "confidence": round(float(result["score"]), 3)}
            except:
                pass
        
        return {"sentiment": "Neutral", "confidence": 0.6}

    def predict_sentiment(self, text):
        return self.predict_sentiment_with_confidence(text)["sentiment"]

_sentiment_analyzer = None

def get_sentiment_analyzer():
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    return _sentiment_analyzer
