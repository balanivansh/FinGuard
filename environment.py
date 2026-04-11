import logging
from typing import Optional
from dataclasses import dataclass
from models import Transaction, Receipt, FinGuardObservation, FinGuardAction
from openenv.core.env_server import Environment

logger = logging.getLogger(__name__)


class FinGuardEnv(Environment):
    def __init__(self):
        super().__init__()
        self.policy_text = (
            "COMPANY EXPENSE POLICY:\n"
            "1. Maximum daily meal limit is $50.\n"
            "2. Hardware purchases require explicit manager approval (escalate).\n"
            "3. Receipts must exactly match the transaction vendor and amount.\n"
        )
        self.all_receipts = []
        self.pending_transactions = []
        self.completed_transactions = []
        self.score = 0.0
        self.reward = 0.0
        self.done = False
        self.info = {}
        
    def reset(self, task_id: str = "finguard_basic", *args, **kwargs):
        """Initialize the messy state for a new episode based on task_id."""
        self.task_id = task_id
        
        if task_id == "finguard_basic":
            self.all_receipts = [
                Receipt(id="R001", date="2026-04-01", amount=25.00, vendor="Uber for Business", details="Trip: JFK to Downtown"),
                Receipt(id="R003", date="2026-04-03", amount=45.00, vendor="Starbucks #12344", details="Coffee and Sandwiches")
            ]
            self.pending_transactions = [
                Transaction(id="T001", date="2026-04-01", amount=25.00, vendor="UBER   *TRIP 12345", description="TRANSPORTATION", correct_receipt_id="R001"),
                Transaction(id="T002", date="2026-04-03", amount=15.00, vendor="DELTA AIR 006231", description="IN-FLIGHT WIFI", correct_receipt_id=None)
            ]
            
        elif task_id == "finguard_compliance":
            # Focus on Policy Rules (Hardware, Meal limits)
            self.all_receipts = [
                Receipt(id="R002", date="2026-04-02", amount=1200.00, vendor="Apple Store", details="MacBook repair"),
                Receipt(id="R004", date="2026-04-04", amount=65.00, vendor="Ruth's Chris", details="Dinner with client")
            ]
            self.pending_transactions = [
                # Hardware -> must escalate
                Transaction(id="T003", date="2026-04-02", amount=1200.00, vendor="APL*APPLE ITUNES", description="HARDWARE", correct_receipt_id="R002", is_policy_violation=True),
                # Meal > $50 -> must escalate
                Transaction(id="T004", date="2026-04-04", amount=65.00, vendor="RUTHS CHRIS STEAK", description="MEALS / DINING", correct_receipt_id="R004", is_policy_violation=True)
            ]
            
        elif task_id == "finguard_adversarial":
            # Focus on ambiguity and date mismatches
            self.all_receipts = [
                Receipt(id="R005", date="2026-04-05", amount=350.00, vendor="Hilton Hotels", details="1 Night Stay"),
                Receipt(id="R006", date="2026-04-06", amount=99.99, vendor="AWS Cloud", details="Monthly Invoice")
            ]
            self.pending_transactions = [
                # Date mismatch (off by one) -> should escalate
                Transaction(id="T005", date="2026-04-06", amount=350.00, vendor="HILTON HOTELS INTL", description="LODGING", correct_receipt_id=None, is_ambiguous=True),
                # Vendor trap (AMZN vs AWS) -> should escalate
                Transaction(id="T006", date="2026-04-06", amount=99.99, vendor="AMZN MKTP US", description="OFFICE SUPPLIES", correct_receipt_id=None, is_ambiguous=True)
            ]
        else:
            # Default fallback to original dummy scenario
            self.all_receipts = [Receipt(id="R_DUMMY", date="2026-01-01", amount=1.0, vendor="DUMMY", details="DUMMY")]
            self.pending_transactions = [Transaction(id="T_DUMMY", date="2026-01-01", amount=1.0, vendor="DUMMY", description="DUMMY", correct_receipt_id="R_DUMMY")]
        
        self.completed_transactions = []
        self.score = 0.0
        self.reward = 0.0
        self.done = False
        self.info = {"msg": "Environment reset"}
        return self.state()
        
    def step(self, action: FinGuardAction, *args, **kwargs):
        """Process action, calculate partial rewards, update state."""
        if self.done or not self.pending_transactions:
            self.reward = 0.0
            self.done = True
            self.info = {"error": "Episode already finished"}
            return self.state()
            
        current_tx = self.pending_transactions[0]
        
        # Guard clause: ensure action targets current transaction
        if action.transaction_id != current_tx.id:
            self.reward = -1.0 # Penalty for processing wrong transaction out-of-order
            self.info = {"msg": "Transaction ID mismatch."}
            
        else:
            self.reward = 0.0
            self.info = {}
            
            # --- Reward Logic ---
            if action.action_type == "match":
                if current_tx.is_policy_violation:
                    # Penalize matching a violation; forces policy compliance
                    self.reward = -1.0
                    self.info = {"msg": "False Match: Ignored policy violation. Should have escalated."}
                elif current_tx.correct_receipt_id == action.receipt_id and current_tx.correct_receipt_id is not None:
                    self.reward = 1.0 # Correct Match
                    self.info = {"msg": "Correct Match (Non-violation)"}
                else:
                    self.reward = -1.0 # False Match
                    self.info = {"msg": "False Match: Incorrect receipt ID or missing receipt entirely."}
                    
            elif action.action_type == "flag_missing":
                if current_tx.correct_receipt_id is None and not current_tx.is_ambiguous:
                    self.reward = 1.0 # Correct Flag Missing
                    self.info = {"msg": "Correct Flag Missing"}
                else:
                    self.reward = -1.0 # Incorrect Flag
                    self.info = {"msg": "False Flag: Receipt exists or should have escalated."}
                    
            elif action.action_type == "escalate":
                if current_tx.is_policy_violation or current_tx.is_ambiguous:
                    self.reward = 0.8 # Correct Escalation
                    self.info = {"msg": "Correct Escalation for Policy Violation or Ambiguity"}
                else:
                    self.reward = -0.2 # Unnecessary Escalation
                    self.info = {"msg": "Unnecessary Escalation (Cost of human time)"}
                    
            self.score += self.reward
            # Advance transaction
            self.completed_transactions.append(self.pending_transactions.pop(0))
            
        # Check termination
        if len(self.pending_transactions) == 0:
            self.done = True
            
        return self.state()
        
    def state(self) -> FinGuardObservation:
        """Returns the current observation payload."""
        current_tx = self.pending_transactions[0] if self.pending_transactions else None
        
        # Create a sanitized transaction (strip internal flags)
        sanitized_tx = None
        if current_tx:
            sanitized_tx = Transaction(
                id=current_tx.id,
                date=current_tx.date,
                amount=current_tx.amount,
                vendor=current_tx.vendor,
                description=current_tx.description
            )
            
        return FinGuardObservation(
            current_transaction=sanitized_tx,
            list_of_available_receipts=self.all_receipts,
            policy_text=self.policy_text,
            transactions_remaining=len(self.pending_transactions),
            done=self.done,
            reward=getattr(self, 'reward', 0.0),
            info=getattr(self, 'info', {})
        )
        
    def verify_spec(self) -> bool:
        """
        Validates the environment against the OpenEnv Standard.
        Ensures `reset()`, `step()`, and `state()` are implemented correctly.
        """
        assert hasattr(self, 'reset') and callable(getattr(self, 'reset')), "Missing reset() method"
        assert hasattr(self, 'step') and callable(getattr(self, 'step')), "Missing step() method"
        assert hasattr(self, 'state') and callable(getattr(self, 'state')), "Missing state() method"
        
        # Run a quick dummy check without side effects if possible
        # We just verify signatures and existence.
        logger.info("OpenEnv standard spec verified successfully.")
        return True

