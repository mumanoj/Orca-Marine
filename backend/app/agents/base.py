from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, Field
from app.domain.evidence import Evidence
from app.tools.registry import BaseTool

class AgentInput(BaseModel):
    latitude: float
    longitude: float
    context: dict[str, Any] = Field(default_factory=dict)

class AgentOutput(BaseModel):
    agent_name: str
    status: str = Field(description="Execution status: completed, failed, degraded")
    evidence: list[Evidence] = Field(default_factory=list, description="Gathered observations")
    messages: list[str] = Field(default_factory=list, description="Agent thoughts/actions logs")
    errors: list[str] = Field(default_factory=list)
    degraded_reason: Optional[str] = None

class BaseAgent(ABC):
    """
    Abstract Base Agent Interface.
    Defines agent responsibility, tool scope, input/output validation, and execution.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def required_tools(self) -> list[str]:
        pass

    @abstractmethod
    async def execute(
        self, 
        input_data: AgentInput, 
        tools: dict[str, BaseTool],
        **kwargs: Any
    ) -> AgentOutput:
        """
        Runs the agent task. Must return structured AgentOutput.
        """
        pass
