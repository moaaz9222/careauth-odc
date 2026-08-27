import asyncio
import json
from typing import Callable, Any, Optional

from contracts.contracts import (
    CoverageStatus,
    DocumentationResult,
    CoverageResult,
    AgentStatus
)
from app.agents.json_repair import repair_json
from app.agents.coverage.coverage_agent import CoverageAgent
from app.agents.documentation.documentation_agent import DocumentationAgent

class Orchestrator:
    def __init__(self):
        self.coverage_agent = CoverageAgent()
        self.documentation_agent = DocumentationAgent()

    async def _run_agent_with_retry(self, agent_func: Callable, *args, **kwargs) -> Any:
        try:
            return await agent_func(*args, **kwargs)
        except Exception as e1:
            print(f"Agent call attempt 1 failed: {e1}, retrying...")
            try:
                return await agent_func(*args, **kwargs)
            except Exception as e2:
                print(f"Agent call attempt 2 failed: {e2}")
                return {"status": AgentStatus.ERROR.value, "error": str(e2)}

    async def run(
        self,
        request_id: str,
        coverage_input,
        documentation_input: dict,
        persist_analysis: Callable,
        emit_event: Callable,
        rule_row: Optional[dict] = None
    ) -> dict:
        
        # Fan out Coverage and Documentation agents in parallel
        cov_task = asyncio.create_task(
            self._run_agent_with_retry(self.coverage_agent.analyze, coverage_input, rule_row=rule_row)
        )
        doc_task = asyncio.create_task(
            self._run_agent_with_retry(self.documentation_agent.analyze, **documentation_input)
        )
        
        cov_res, doc_res = await asyncio.gather(cov_task, doc_task)
        
        is_cov_error = isinstance(cov_res, dict) and cov_res.get("status") == AgentStatus.ERROR.value
        is_doc_error = isinstance(doc_res, dict) and doc_res.get("status") == AgentStatus.ERROR.value
        
        if not is_cov_error and not is_doc_error:
            # Deterministic combined rule per §12:
            # ready_for_submission = (coverage.status in ("covered", "prior_authorization_required") 
            #                         and coverage.status != "unknown" and documentation.ready_for_submission)
            cov_status_val = cov_res.status.value if hasattr(cov_res.status, 'value') else str(cov_res.status)
            ready_for_submission = bool(
                cov_status_val in (CoverageStatus.COVERED.value, CoverageStatus.PRIOR_AUTHORIZATION_REQUIRED.value)
                and cov_status_val != CoverageStatus.UNKNOWN.value
                and doc_res.ready_for_submission
            )
        else:
            # A failed agent NEVER yields an optimistic result per §22
            ready_for_submission = False

        result = {
            "ready_for_submission": ready_for_submission,
            "coverage": cov_res.model_dump() if not is_cov_error else cov_res,
            "documentation": doc_res.model_dump() if not is_doc_error else doc_res,
        }
        
        await persist_analysis(request_id, result)
        await emit_event("ANALYSIS_COMPLETE", result)
        
        return result
