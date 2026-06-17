# orchestrator.py
import time
from config import L1_SYSTEM, L2_SYSTEM_ISOLATED, L2_SYSTEM_HYBRID, MODELS
from client import call_llm_async

async def run_single_mode(prompt_text: str) -> dict:
    """Simulates a single-call monolithic model."""
    start_time = time.time()
    
    # Simulate: One system prompt that tries to do both roles
    unified_system = f"{L1_SYSTEM}\n\nBefore answering, silently check for safety. If unsafe, refuse."
    
    raw_content, parsed = await call_llm_async(unified_system, prompt_text, MODELS["standard"])
    
    duration = int((time.time() - start_time) * 1000)
    
    return {
        "mode": "single_call",
        "l1_output": raw_content,
        "l2_decision": "N/A (Unified)",
        "l2_confidence": 0,
        "l2_reason": "Single model self-regulation",
        "final_output": raw_content,
        "latency_ms": duration
    }

async def run_isolated_mode(prompt_text: str) -> dict:
    """
    Strictly ISOLATED mode.
    L1 generates -> L2 reviews ONLY the output.
    CRITICAL: The 'prompt_text' is NEVER passed to L2.
    """
    start_time = time.time()
    
    # Step 1: L1 Execution
    l1_raw, l1_parsed = await call_llm_async(L1_SYSTEM, prompt_text, MODELS["standard"])
    
    # Step 2: L2 Review (ISOLATED)
    # Construct input WITHOUT the original prompt
    l2_user_content = f"L1 Generated Output:\n{l1_raw}"
    
    l2_raw, l2_parsed = await call_llm_async(L2_SYSTEM_ISOLATED, l2_user_content, MODELS["standard"])
    
    duration = int((time.time() - start_time) * 1000)
    
    # Parse results safely
    decision = l2_parsed.get("decision", "UNKNOWN")
    confidence = int(l2_parsed.get("confidence", 0)) if isinstance(l2_parsed.get("confidence"), (int, float)) else 0
    reason = l2_parsed.get("reason", "No reason provided")
    
    final_out = l1_raw if decision == "ALLOW" else "BLOCKED"

    return {
        "mode": "isolated_call",
        "l1_output": l1_raw,
        "l2_decision": decision,
        "l2_confidence": confidence,
        "l2_reason": reason,
        "final_output": final_out,
        "latency_ms": duration
    }

async def run_hybrid_mode(prompt_text: str) -> dict:
    """
    HYBRID mode.
    L1 generates -> L2 reviews Output + Prompt.
    """
    start_time = time.time()
    
    # Step 1: L1 Execution
    l1_raw, l1_parsed = await call_llm_async(L1_SYSTEM, prompt_text, MODELS["standard"])
    
    # Step 2: L2 Review (HYBRID)
    # Includes prompt context
    l2_user_content = f"Original Prompt:\n{prompt_text}\n\nL1 Generated Output:\n{l1_raw}"
    
    l2_raw, l2_parsed = await call_llm_async(L2_SYSTEM_HYBRID, l2_user_content, MODELS["standard"])
    
    duration = int((time.time() - start_time) * 1000)
    
    decision = l2_parsed.get("decision", "UNKNOWN")
    confidence = int(l2_parsed.get("confidence", 0)) if isinstance(l2_parsed.get("confidence"), (int, float)) else 0
    reason = l2_parsed.get("reason", "No reason provided")
    
    final_out = l1_raw if decision == "ALLOW" else "BLOCKED"

    return {
        "mode": "hybrid_call",
        "l1_output": l1_raw,
        "l2_decision": decision,
        "l2_confidence": confidence,
        "l2_reason": reason,
        "final_output": final_out,
        "latency_ms": duration
    }
