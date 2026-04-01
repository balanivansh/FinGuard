import os
import json
import logging
import time
from openai import OpenAI
from environment import FinGuardEnv
from models import FinGuardAction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Load configuration
    api_key = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
    api_base_url = os.getenv("API_BASE_URL")
    model_name = os.getenv("MODEL_NAME", "gemini-3-flash-preview")

    if not api_key:
        logger.warning("No API key environment variable found. OpenAI calls will fail if not authenticated.")

    # Initialize OpenAI Client
    client_kwargs = {"api_key": api_key}
    if api_base_url:
        client_kwargs["base_url"] = api_base_url
        
    client = OpenAI(**client_kwargs)

    # Initialize Environment
    env = FinGuardEnv()
    observation = env.reset()
    logger.info("Environment initialized.")

    action_log = []

    # System instruction guiding the LLM as requested
    system_prompt = (
        "You are an expert 'Risk-Averse Auditor'. You are tasked with auditing corporate bank transactions.\n"
        "You must strictly prioritize company policy over everything else.\n"
        "Your available actions for a transaction are to 'match' it to a valid receipt, 'flag_missing' if there "
        "is no receipt, or 'escalate' if there is a policy violation or any doubt/ambiguity (such as mismatched dates or questionable items).\n"
        "Pay extreme attention to dates, amounts, and policy rules.\n"
        "Always output your choice strictly as a JSON object that matches the FinGuardAction schema:\n"
        '{"action_type": "match"|"flag_missing"|"escalate", "transaction_id": "...", "receipt_id": "..." (optional), "reason": "..." (optional)}\n'
    )

    while not env.done:
        # Prepare context for the prompt
        user_prompt = f"Current State:\n{observation.model_dump_json(indent=2)}\n\nWhat is your action?"

        max_retries = 3
        retry_delay = 5.0
        response = None
        
        for attempt in range(max_retries):
            try:
                # Call LLM
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    timeout=60.0
                )
                break # success
            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2 # exponential backoff
                else:
                    logger.error("Max retries reached. Aborting this step.")
        
        if not response:
            break
            
        try:
            # Parse raw response
            raw_content = response.choices[0].message.content
            action_data = json.loads(raw_content)
            
            # Validate with Pydantic model
            action = FinGuardAction(**action_data)
            logger.info(f"Auditor chose action: {action.action_type} for TX {action.transaction_id}")
            
            # Step the environment
            observation = env.step(action)
            logger.info(f"Step Result: Reward={observation.reward}, Info={observation.info}")
            
            action_log.append({
                "transaction_id": action.transaction_id,
                "action": action.action_type,
                "reward": observation.reward,
                "info": observation.info
            })

        except Exception as e:
            logger.error(f"Error during parsing or step: {e}")
            break

    # Final Summary
    print(f"Final Score: {round(env.score, 2)}")
    for log in action_log:
        print(f"TX: {log['transaction_id']} | Action: {log['action']} | Reward: {log['reward']} | Note: {log['info'].get('msg')}")

if __name__ == "__main__":
    main()
