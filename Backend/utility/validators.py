"""
Custom validators for RAG pipeline:
1. RuleBasedValidator       - before NeMo Guardrails
2. GroundingValidator       - after Reranker, before LLM
3. OutputBusinessValidator  - after LLM, before response
"""
import os
import re
import numpy as np
from dotenv import load_dotenv

load_dotenv("unified.env")

# Configurable word lists (add your own)
RESTRICTED_TOPICS = [
    "unrelated products", "executive compensation detail",
    "internal pricing", "trade secrets",
    "merger acquisition", "legal proceedings",
]

CONFIDENTIAL_KEYWORDS = [
    "password", "secret key", "api key", "accesstoken",
    "ssn", "social security number", "credit card number","private key",
    "bank account number", "personal identification",
]

COMPETITOR_NAMES = [
    # Add your company's competitors here
    "competitor1", "competitor2",
]

POLICY_VIOLATIONS = [
    "bypass", "ignore previous instructions","ignore all instructions",
    "disregard", "pretend you are","do anything now",
    "act as if", "jailbreak",
]

GROUNDING_THRESHOLD = float(
    os.getenv("GROUNDING_THRESHOLD", "0.35")
)


# ------------------------------------------------------------------
# 1. RULE-BASED VALIDATION LAYER
# ------------------------------------------------------------------

class RuleBasedValidator:
    """
    Pure Python rule engine - runs BEFORE NeMo Guardrails.
    Checks restricted topics, confidential keywords,
    competitor mentions, and enterprise policy enforcement.
    Zero API calls - instant.
    """

    def validate(self, query: str) -> dict:
        query_lower = query.lower()

        # Check 1 - Restricted topics
        for topic in RESTRICTED_TOPICS:
            if topic.lower() in query_lower:
                print(f"[RuleValidator] BLOCKED - restricted topic: {topic}")
                return {
                    "allowed": False,
                    "reason": "restricted_topic",
                    "message": (
                        f"This query touches a restricted topic "
                        f"({topic}) and cannot be processed."
                    )
                }

        # Check 2 - Confidential keywords
        for keyword in CONFIDENTIAL_KEYWORDS:
            if keyword.lower() in query_lower:
                print(f"[RuleValidator] BLOCKED - confidential keyword: {keyword}")
                return {
                    "allowed": False,
                    "reason": "confidential_keyword",
                    "message": (
                        "This query contains sensitive information "
                        "that cannot be processed."
                    )
                }

        # Check 3 - Competitor mentions
        for competitor in COMPETITOR_NAMES:
            if competitor.lower() in query_lower:
                print(f"[RuleValidator] BLOCKED - competitor mention: {competitor}")
                return {
                    "allowed": False,
                    "reason": "competitor_mention",
                    "message": (
                        "Queries about competitor organizations "
                        "cannot be processed."
                    )
                }

        # Check 4 - Policy violations (prompt injection attempts)
        for violation in POLICY_VIOLATIONS:
            if violation.lower() in query_lower:
                print(f"[RuleValidator] BLOCKED - policy violation: {violation}")
                return {
                    "allowed": False,
                    "reason": "policy_violation",
                    "message": (
                        "This request violates enterprise policy "
                        "and cannot be processed."
                    )
                }

        print("[RuleValidator] PASSED")
        return {"allowed": True}


# ------------------------------------------------------------------
# 2. GROUNDING VALIDATOR LAYER
# ------------------------------------------------------------------

class GroundingValidator:
    """
    Validates that retrieved chunks are relevant enough
    to ground the LLM response.
    Runs AFTER reranker, BEFORE LLM.
    Prevents hallucination by rejecting low-relevance context.
    """

    def validate(
        self,
        query: str,
        chunks: list[dict],
    ) -> dict:
        if not chunks:
            print("[GroundingValidator] BLOCKED - no chunks retrieved")
            return {
                "allowed": False,
                "reason": "no_context",
                "message": (
                    "No relevant information was found in the "
                    "documents to answer your question."
                ),
                "chunks": [],
            }

        try:
            from utility.embedding_config import (
                create_embedding_vector,
                get_embedding_client,
            )

            client    = get_embedding_client()
            query_vec = create_embedding_vector(
                client, query, input_type="query"
            )

            # Score each chunk against the query
            scored_chunks = []
            for chunk in chunks:
                content = chunk.get("content", "")
                if not content.strip():
                    continue

                chunk_vec = create_embedding_vector(
                    client, content, input_type="passage"
                )

                # Cosine similarity
                a = np.array(query_vec)
                b = np.array(chunk_vec)
                score = float(
                    np.dot(a, b) /
                    (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
                )
                scored_chunks.append({**chunk, "grounding_score": score})

            if not scored_chunks:
                return {
                    "allowed": False,
                    "reason": "no_valid_chunks",
                    "message": "No valid context found.",
                    "chunks": [],
                }

            # Check best score against threshold
            best_score = max(c["grounding_score"] for c in scored_chunks)
            print(
                f"[GroundingValidator] Best score: {best_score:.4f} "
                f"(threshold: {GROUNDING_THRESHOLD})"
            )

            if best_score < GROUNDING_THRESHOLD:
                print("[GroundingValidator] BLOCKED - context not relevant enough")
                return {
                    "allowed": False,
                    "reason": "low_relevance",
                    "message": (
                        "The retrieved context is not relevant enough "
                        "to answer your question reliably."
                    ),
                    "chunks": [],
                }

            # Filter chunks above threshold and sort by score
            valid_chunks = [
                c for c in scored_chunks
                if c["grounding_score"] >= GROUNDING_THRESHOLD
            ]
            valid_chunks.sort(
                key=lambda x: x["grounding_score"], reverse=True
            )

            print(
                f"[GroundingValidator] PASSED - "
                f"{len(valid_chunks)} valid chunks"
            )
            return {
                "allowed": True,
                "chunks": valid_chunks,
            }

        except Exception as e:
            print(f"[GroundingValidator] Error: {e} - passing through")
            return {"allowed": True, "chunks": chunks}


# ------------------------------------------------------------------
# 3. OUTPUT BUSINESS VALIDATOR
# ------------------------------------------------------------------

OUTPUT_SENSITIVE_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",           # SSN pattern
    r"\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b",  # Credit card
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
    r"\bpassword\s*[:=]\s*\S+",          # Password leakage
    r"\bapi[_-]?key\s*[:=]\s*\S+",      # API key leakage
]

OUTPUT_CONFIDENTIAL_TERMS = [
    "internal only", "confidential", "do not share",
    "trade secret", "proprietary", "not for distribution",
]


class OutputBusinessValidator:
    """
    Final validation layer AFTER LLM generates response.
    Checks for sensitive data leakage, confidential info,
    competitor mentions, and policy violations in the output.
    """

    def validate(self, response_text: str) -> dict:
        if not response_text or not response_text.strip():
            return {"allowed": True, "text": response_text}

        response_lower = response_text.lower()

        # Check 1 - Sensitive data patterns (PII)
        for pattern in OUTPUT_SENSITIVE_PATTERNS:
            if re.search(pattern, response_text, re.IGNORECASE):
                print("[OutputValidator] BLOCKED - sensitive data pattern")
                return {
                    "allowed": False,
                    "reason": "sensitive_data",
                    "text": (
                        "The response was blocked as it may contain "
                        "sensitive personal information."
                    )
                }

        # Check 2 - Confidential terms in output
        for term in OUTPUT_CONFIDENTIAL_TERMS:
            if term.lower() in response_lower:
                print(f"[OutputValidator] BLOCKED - confidential term: {term}")
                return {
                    "allowed": False,
                    "reason": "confidential_content",
                    "text": (
                        "The response was blocked as it may contain "
                        "confidential information."
                    )
                }

        # Check 3 - Competitor mentions in output
        for competitor in COMPETITOR_NAMES:
            if competitor.lower() in response_lower:
                print("[OutputValidator] FILTERED - competitor mention removed")
                response_text = re.sub(
                    competitor, "[competitor]",
                    response_text, flags=re.IGNORECASE
                )

        print("[OutputValidator] PASSED")
        return {"allowed": True, "text": response_text}


# Singleton instances
rule_validator      = RuleBasedValidator()
grounding_validator = GroundingValidator()
output_validator    = OutputBusinessValidator()
