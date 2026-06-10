# entity_extractor.py - UPDATED VERSION
import re
from typing import Dict, Optional

class EntityExtractor:
    def __init__(self):
        self.patterns = {
            'order_id': [
                r'order[\s#:-]*([A-Z0-9-]{5,20})',
                r'ord(?:er)?[\s]*[#:]*[\s]*(\d{5,12})',
                r'#(\d{8,12})',
                r'order[\s]*number[\s:]*([A-Z0-9-]+)'
            ],
            'transaction_id': [
                r'transaction[\s#:-]*([A-Z0-9-]{8,30})',
                r'txn[\s#:-]*([A-Z0-9-]{8,20})',
                r'paypal[\s#]*([A-Z0-9]{10,20})',
                r'transaction[\s]*id[\s:]*([A-Z0-9-]+)'
            ],
            'amount': [
                r'\$\s*(\d+(?:\.\d{2})?)',
                r'(\d+(?:\.\d{2})?)\s*(?:USD|dollars|usd)',
                r'(\d+(?:\.\d{2})?)\s*\$'
            ],
            'error_code': [
                # Priority order - more specific patterns first
                r'(0x[0-9A-Fa-f]{4,16})',  # Hex codes like 0x80070005
                r'error[\s:]+([A-Z0-9_]{3,30})',  # Error: XYZ_123
                r'code[\s:]+(\d{3,6})',  # Code: 500
                r'(ERR_?[A-Z_0-9]+)',  # ERR_CONNECTION
                r'\[([A-Z0-9_-]+)\]',  # [ERROR_CODE]
            ],
            'account_email': [
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            ],
            'customer_id': [
                r'customer[\s#:-]*([A-Z0-9-]{5,20})',
                r'cust[\s#:-]*(\d{5,10})',
                r'id[\s:]*([A-Z0-9]{6,15})',
                r'user[\s]*id[\s:]*([A-Z0-9-]+)'
            ],
            'product': [
                r'(subscription|premium|basic|enterprise|pro)(?:\s+plan)?',
                r'(windows|mac|ios|android)(?:\s+app)?',
                r'(vpn|printer|router|firewall|server|app|software)',
                r'product[\s:]*([A-Za-z0-9\s-]{3,30})'
            ],
            'time': [
                r'(yesterday|today|last\s+(?:week|month|day|hour))',
                r'(\d+)\s*(?:hour|day|minute|week|month)s?\s*ago',
                r'(on\s+\w+\s+\d{1,2}(?:st|nd|rd|th)?)',
                r'(\d{1,2}:\d{2}\s*(?:AM|PM)?)'
            ],
            'requested_action': [
                r'\b(refund|cancel|reset|change|update|delete|export|import|fix|repair|replace)\b',
                r'need\s+(\w+(?:\s+\w+)?)',
                r'would like to (\w+(?:\s+\w+)?)'
            ],
            'plan': [
                r'\b(basic|premium|enterprise|pro|free|trial)\b(?:\s+plan)?',
                r'\b(annual|monthly|weekly)\b(?:\s+plan)?'
            ]
        }
    
    def extract_entities(self, text: str) -> Dict[str, Optional[str]]:
        """Extract all entities from text"""
        entities = {}
        
        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    value = value.strip()
                    
                    # Special handling for error_code - clean it
                    if entity_type == 'error_code':
                        # Clean up common prefixes
                        value = re.sub(r'^(error|code)[:\s]*', '', value, flags=re.IGNORECASE)
                    
                    entities[entity_type] = value
                    break
        
        return entities
    
    def extract_all(self, text: str) -> Dict:
        """Extract entities with metadata"""
        entities = self.extract_entities(text)
        
        has_priority_entity = any(
            key in entities for key in ['order_id', 'transaction_id', 'amount', 'error_code']
        )
        
        return {
            "extracted_entities": entities,
            "entity_count": len(entities),
            "has_order_info": 'order_id' in entities or 'transaction_id' in entities,
            "has_error_info": 'error_code' in entities,
            "has_amount_info": 'amount' in entities,
            "has_customer_info": 'account_email' in entities or 'customer_id' in entities,
            "priority_entities_found": has_priority_entity
        }

# Global instance
_entity_extractor = None

def get_entity_extractor():
    global _entity_extractor
    if _entity_extractor is None:
        _entity_extractor = EntityExtractor()
    return _entity_extractor