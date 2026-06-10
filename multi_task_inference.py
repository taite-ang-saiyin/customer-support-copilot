import json
import re
from pathlib import Path

import torch
import torch.nn as nn
from transformers import AutoTokenizer, DebertaV2Config, DebertaV2Model


class MultiTaskTicketModel(nn.Module):
    def __init__(self, encoder_config, num_categories, num_priorities):
        super().__init__()
        self.encoder = DebertaV2Model(encoder_config)
        hidden_size = self.encoder.config.hidden_size
        self.dropout = nn.Dropout(0.2)
        self.category_head = nn.Linear(hidden_size, num_categories)
        self.priority_head = nn.Linear(hidden_size, num_priorities)

    def forward(self, input_ids=None, attention_mask=None):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        pooled = outputs.last_hidden_state[:, 0]
        pooled = self.dropout(pooled)
        category_logits = self.category_head(pooled)
        priority_logits = self.priority_head(pooled)
        return category_logits, priority_logits


class MultiTaskPredictor:
    def __init__(self, model_path="models/ticket_multitask_model"):
        self.model_path = Path(model_path)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[model] Loading model from {self.model_path} on {self.device}...")

        with open(self.model_path / "config.json", "r", encoding="utf-8") as f:
            self.config = json.load(f)

        with open(self.model_path / "label_mappings.json", "r", encoding="utf-8") as f:
            self.label_mappings = json.load(f)

        checkpoint = torch.load(self.model_path / "model_weights.pt", map_location="cpu")
        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            checkpoint = checkpoint["model_state_dict"]

        encoder_config = self._build_encoder_config(checkpoint)
        self.model = MultiTaskTicketModel(
            encoder_config=encoder_config,
            num_categories=self.config["num_categories"],
            num_priorities=self.config["num_priorities"],
        )
        self.model.load_state_dict(checkpoint, strict=True)
        self.model.to(self.device).float()
        self.model.eval()

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, extra_special_tokens={})
        self.max_length = int(self.config.get("max_length", 128))

        print("[model] Model loaded successfully!")
        print(f"   Base model: {self.config.get('base_model', 'local-deberta')}")
        print(f"   Categories: {self.label_mappings['categories']}")
        print(f"   Priorities: {self.label_mappings['priorities']}")

    def _build_encoder_config(self, checkpoint):
        """Build the DeBERTa-v3-base config locally so inference works offline."""
        word_embeddings = checkpoint["encoder.embeddings.word_embeddings.weight"]
        intermediate = checkpoint["encoder.encoder.layer.0.intermediate.dense.weight"]
        category_head = checkpoint["category_head.weight"]
        priority_head = checkpoint["priority_head.weight"]

        hidden_size = int(word_embeddings.shape[1])
        num_layers = len(
            {
                int(match.group(1))
                for key in checkpoint
                for match in [re.search(r"encoder\.encoder\.layer\.(\d+)\.", key)]
                if match
            }
        )

        if int(category_head.shape[0]) != self.config["num_categories"]:
            raise ValueError("Category head size does not match config.json")
        if int(priority_head.shape[0]) != self.config["num_priorities"]:
            raise ValueError("Priority head size does not match config.json")

        return DebertaV2Config(
            vocab_size=int(word_embeddings.shape[0]),
            hidden_size=hidden_size,
            num_hidden_layers=num_layers,
            num_attention_heads=12,
            intermediate_size=int(intermediate.shape[0]),
            hidden_act="gelu",
            hidden_dropout_prob=0.1,
            attention_probs_dropout_prob=0.1,
            max_position_embeddings=512,
            type_vocab_size=0,
            initializer_range=0.02,
            layer_norm_eps=1e-7,
            relative_attention=True,
            max_relative_positions=-1,
            position_buckets=256,
            norm_rel_ebd="layer_norm",
            position_biased_input=False,
            pos_att_type=["p2c", "c2p"],
            share_att_key=True,
            pooler_dropout=0,
            pooler_hidden_act="gelu",
        )

    def _clean_text(self, text):
        if not isinstance(text, str):
            return ""
        text = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL]", text)
        text = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP_ADDRESS]", text)
        return " ".join(text.split())

    def predict(self, text):
        try:
            cleaned_text = self._clean_text(text)
            tokenized = self.tokenizer(
                cleaned_text,
                truncation=True,
                padding="max_length",
                max_length=self.max_length,
                return_tensors="pt",
            )

            tokenized.pop("token_type_ids", None)
            inputs = {key: value.to(self.device) for key, value in tokenized.items()}

            with torch.no_grad():
                category_logits, priority_logits = self.model(**inputs)

            category_probs = torch.softmax(category_logits, dim=1)[0]
            priority_probs = torch.softmax(priority_logits, dim=1)[0]
            category_idx = torch.argmax(category_probs).item()
            priority_idx = torch.argmax(priority_probs).item()

            category = self.label_mappings["categories"][category_idx]
            priority = self.label_mappings["priorities"][priority_idx]

            return {
                "category": category,
                "priority": priority,
                "confidences": {
                    "category": round(category_probs[category_idx].item(), 3),
                    "priority": round(priority_probs[priority_idx].item(), 3),
                },
            }
        except Exception as e:
            print(f"Prediction error: {e}")
            return {
                "category": "General",
                "priority": "Medium",
                "confidences": {"category": 0.5, "priority": 0.5},
            }


_predictor = None


def get_predictor():
    global _predictor
    if _predictor is None:
        _predictor = MultiTaskPredictor()
    return _predictor
