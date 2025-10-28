"""
AI Output Schemas
These schemas define the contract for AI agent outputs.

IMPORTANT: Batch processor MUST output these exact schemas.
Frontend expects these structures in the database.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ============================================================================
# AGENT 1: CLASSIFICATION
# ============================================================================

class EntityExtraction(BaseModel):
    """Extracted entities from thought text."""
    people: List[str] = Field(default_factory=list)
    dates: List[str] = Field(default_factory=list)
    places: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)


class ClassificationOutput(BaseModel):
    """
    Output schema for Classification Agent (Agent 1).
    
    Contract:
    - type: Must be one of the defined literal values
    - urgency: Must be one of the defined literal values
    - All fields are required
    """
    type: Literal['task', 'problem', 'idea', 'question', 'observation', 'emotion']
    urgency: Literal['immediate', 'soon', 'eventually', 'never']
    entities: EntityExtraction
    emotional_tone: str
    implied_needs: List[str] = Field(default_factory=list)


# ============================================================================
# AGENT 2: ANALYSIS
# ============================================================================

class GoalAlignment(BaseModel):
    """Goal alignment analysis."""
    aligned_goals: List[str] = Field(default_factory=list)
    conflicting_goals: List[str] = Field(default_factory=list)
    reasoning: str


class RealisticAssessment(BaseModel):
    """Feasibility assessment."""
    feasibility: str
    constraints: List[str] = Field(default_factory=list)


class AnalysisOutput(BaseModel):
    """
    Output schema for Analysis Agent (Agent 2).
    
    Contract:
    - Provides contextual analysis based on user profile
    - All fields are required
    """
    goal_alignment: GoalAlignment
    underlying_needs: List[str] = Field(default_factory=list)
    pattern_connections: List[str] = Field(default_factory=list)
    realistic_assessment: RealisticAssessment
    unspoken_factors: List[str] = Field(default_factory=list)


# ============================================================================
# AGENT 3: VALUE IMPACT
# ============================================================================

class ValueScore(BaseModel):
    """Value score with reasoning."""
    score: int = Field(..., ge=0, le=10)
    reasoning: str


class ValueImpactOutput(BaseModel):
    """
    Output schema for Value Impact Agent (Agent 3).
    
    Contract:
    - All scores must be 0-10
    - weighted_total is calculated from individual scores
    """
    economic_value: ValueScore
    relational_value: ValueScore
    legacy_value: ValueScore
    health_value: ValueScore
    growth_value: ValueScore
    weighted_total: float = Field(..., ge=0, le=10)
    overall_assessment: str


# ============================================================================
# AGENT 4: ACTION PLAN
# ============================================================================

class QuickWin(BaseModel):
    """Quick win action item."""
    action: str
    duration: str
    timing: str


class MainAction(BaseModel):
    """Main action item with details."""
    action: str
    duration: str
    prerequisites: List[str] = Field(default_factory=list)
    obstacles: List[str] = Field(default_factory=list)
    mitigation: str
    timing: str


class ActionPlanOutput(BaseModel):
    """
    Output schema for Action Planning Agent (Agent 4).
    
    Contract:
    - quick_wins: 0-5 immediate actions
    - main_actions: 1-10 primary actions
    """
    quick_wins: List[QuickWin] = Field(default_factory=list)
    main_actions: List[MainAction] = Field(default_factory=list)
    delegation_opportunities: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)


# ============================================================================
# AGENT 5: PRIORITY
# ============================================================================

class RecommendedTimeline(BaseModel):
    """Recommended timeline for action."""
    start: str
    duration: str
    checkpoints: List[str] = Field(default_factory=list)


class PriorityOutput(BaseModel):
    """
    Output schema for Priority Agent (Agent 5).
    
    Contract:
    - priority_level: Must be one of the defined literal values
    """
    priority_level: Literal['Critical', 'High', 'Medium', 'Low', 'Defer']
    urgency_reasoning: str
    strategic_fit: str
    recommended_timeline: RecommendedTimeline
    final_recommendation: str


# ============================================================================
# GROUP MODE: CONSOLIDATED OUTPUT
# ============================================================================

class DivergentView(BaseModel):
    """Divergent viewpoint from a persona."""
    persona: str
    viewpoint: str


class ConsolidatedOutput(BaseModel):
    """
    Output schema for consolidated persona analysis (Group Mode).
    
    Contract:
    - Only present when processing_mode='group'
    - Synthesizes outputs from all personas
    """
    summary: str
    key_insights: List[str] = Field(default_factory=list)
    consensus_points: List[str] = Field(default_factory=list)
    divergent_views: List[DivergentView] = Field(default_factory=list)
    recommended_action: str
    personas_processed: int
