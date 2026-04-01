from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class Transaction(BaseModel):
    id: str
    date: str
    amount: float
    vendor: str
    description: str
    # Internal flags for simulation logic
    is_policy_violation: bool = Field(False, exclude=True)
    is_ambiguous: bool = Field(False, exclude=True)
    correct_receipt_id: Optional[str] = Field(None, exclude=True)

class Receipt(BaseModel):
    id: str
    date: str
    amount: float
    vendor: str
    details: str

class FinGuardObservation(BaseModel):
    current_transaction: Optional[Transaction] = Field(None, description="The transaction currently being audited.")
    list_of_available_receipts: List[Receipt] = Field(default_factory=list, description="List of all available digital receipts.")
    policy_text: str = Field("", description="The company expense policy.")
    transactions_remaining: int = Field(0, description="Number of transactions left to audit.")
    done: bool = Field(False, description="Whether the audit session is complete.")

class FinGuardAction(BaseModel):
    action_type: Literal["match", "flag_missing", "escalate"] = Field(description="The action to take on the current transaction.")
    transaction_id: str = Field(description="The ID of the transaction being processed.")
    receipt_id: Optional[str] = Field(None, description="Required if action_type is 'match'.")
    reason: Optional[str] = Field(None, description="Required if action_type is 'escalate'.")
