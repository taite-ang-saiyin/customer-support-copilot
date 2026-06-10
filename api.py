from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from entity_extractor import get_entity_extractor
from multi_task_inference import get_predictor
from sentiment_model import get_sentiment_analyzer


app = FastAPI(
    title="Ticket Intelligence API",
    description="Ticket category, priority, sentiment, and entity extraction API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TicketRequest(BaseModel):
    message: str = Field(..., description="Customer message text", min_length=1, max_length=5000)
    ticket_id: Optional[str] = Field(None, description="Optional ticket ID", max_length=50)


class ConfidenceBreakdownResponse(BaseModel):
    category: float = Field(..., description="Category model confidence", ge=0, le=1)
    priority: float = Field(..., description="Priority model confidence", ge=0, le=1)
    sentiment: float = Field(..., description="Sentiment confidence", ge=0, le=1)
    entity: float = Field(..., description="Entity extraction confidence", ge=0, le=1)


class PredictionsResponse(BaseModel):
    category: str = Field(..., description="Support category predicted by the model")
    priority: str = Field(..., description="Priority level predicted by the model")
    sentiment: str = Field(..., description="Customer sentiment")
    confidence: float = Field(..., description="Overall confidence score", ge=0, le=1)
    confidence_breakdown: ConfidenceBreakdownResponse


class EntitiesResponse(BaseModel):
    extracted_entities: Dict[str, Any]
    entity_count: int
    has_order_info: bool
    has_error_info: bool
    has_amount_info: bool
    has_customer_info: bool
    priority_entities_found: bool


class AnalyzeResponse(BaseModel):
    status: str
    message: str
    predictions: PredictionsResponse
    entities: EntitiesResponse
    ticket_id: Optional[str] = None
    timestamp: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str
    model_loaded: bool
    categories_count: int
    timestamp: str


class TaxonomyResponse(BaseModel):
    categories: List[str]
    priorities: List[str]
    sentiments: List[str]
    entities: List[str]


def calculate_entity_confidence(entities: Dict[str, Any]) -> float:
    entity_count = int(entities.get("entity_count", 0))
    if entity_count == 0:
        return 0.5

    confidence = 0.65 + min(entity_count, 5) * 0.07
    if entities.get("priority_entities_found"):
        confidence += 0.1
    return round(min(confidence, 1.0), 3)


def calculate_overall_confidence(
    category_confidence: float,
    priority_confidence: float,
    sentiment_confidence: float,
    entity_confidence: float,
) -> float:
    weights = {
        "category": 0.4,
        "priority": 0.3,
        "sentiment": 0.2,
        "entity": 0.1,
    }
    return round(
        category_confidence * weights["category"]
        + priority_confidence * weights["priority"]
        + sentiment_confidence * weights["sentiment"]
        + entity_confidence * weights["entity"],
        3,
    )


@app.post("/tickets/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_ticket(ticket: TicketRequest):
    """
    Analyze a support ticket.
    
    """
    if not ticket.message or not ticket.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    try:
        predictor = get_predictor()
        ml_result = predictor.predict(ticket.message)

        sentiment_analyzer = get_sentiment_analyzer()
        sentiment_result = sentiment_analyzer.predict_sentiment_with_confidence(ticket.message)

        entity_extractor = get_entity_extractor()
        entities = entity_extractor.extract_all(ticket.message)

        category_confidence = ml_result["confidences"]["category"]
        priority_confidence = ml_result["confidences"]["priority"]
        sentiment_confidence = sentiment_result["confidence"]
        entity_confidence = calculate_entity_confidence(entities)
        confidence_breakdown = {
            "category": round(category_confidence, 3),
            "priority": round(priority_confidence, 3),
            "sentiment": round(sentiment_confidence, 3),
            "entity": round(entity_confidence, 3),
        }
        overall_confidence = calculate_overall_confidence(
            category_confidence,
            priority_confidence,
            sentiment_confidence,
            entity_confidence,
        )

        return {
            "status": "success",
            "message": ticket.message,
            "predictions": {
                "category": ml_result["category"],
                "priority": ml_result["priority"],
                "sentiment": sentiment_result["sentiment"],
                "confidence": overall_confidence,
                "confidence_breakdown": confidence_breakdown,
            },
            "entities": entities,
            "ticket_id": ticket.ticket_id,
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction error: {exc}") from exc


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    try:
        predictor = get_predictor()
        return {
            "status": "healthy",
            "model_loaded": True,
            "categories_count": len(predictor.label_mappings["categories"]),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception:
        return {
            "status": "unhealthy",
            "model_loaded": False,
            "categories_count": 0,
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/taxonomy", response_model=TaxonomyResponse, tags=["System"])
async def get_taxonomy():
    predictor = get_predictor()
    return {
        "categories": predictor.label_mappings["categories"],
        "priorities": predictor.label_mappings["priorities"],
        "sentiments": ["Angry", "Frustrated", "Confused", "Neutral", "Positive"],
        "entities": [
            "order_id",
            "transaction_id",
            "amount",
            "product",
            "error_code",
            "account_email",
            "customer_id",
            "time",
            "requested_action",
            "plan",
        ],
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "Ticket Intelligence API",
        "version": "1.0.0",
        "description": "Support ticket category, priority, sentiment, and entity extraction system",
        "status": "operational",
        "endpoints": {
            "POST /tickets/analyze": "Analyze a support ticket",
            "GET /health": "Health check",
            "GET /taxonomy": "Get model label taxonomy",
            "GET /docs": "Interactive API documentation",
        },
    }
