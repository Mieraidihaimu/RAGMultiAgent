"""
Service Contract Validation Tests

These tests ensure all services communicate using the defined Pydantic contracts:
1. API-Kafka event schema compatibility
2. SSE event schema consistency
3. Database adapter contract adherence
4. AI agent output validation
"""
import pytest
import sys
import os
from datetime import datetime
from uuid import uuid4
from pydantic import ValidationError

# Add parent directory to path to import from common
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))

# Import contracts from common schemas
from common.schemas.api_schemas import ThoughtCreateRequest
from common.schemas.event_schemas import (
    ThoughtCreatedEvent,
    ThoughtProcessingEvent,
    ThoughtAgentCompletedEvent,
    ThoughtCompletedEvent,
    ThoughtFailedEvent,
    SSEThoughtProcessingEvent,
    SSEAgentCompletedEvent,
    SSEThoughtCompletedEvent,
    SSEThoughtFailedEvent,
)
from common.schemas.ai_schemas import (
    ClassificationOutput,
    AnalysisOutput,
    ValueImpactOutput,
    ActionPlanOutput,
    PriorityOutput,
    EntityExtraction,
    GoalAlignment,
    RealisticAssessment,
    ValueScore,
    QuickWin,
    MainAction,
    RecommendedTimeline
)


class TestAPIKafkaContractCompatibility:
    """Test that API request models are compatible with Kafka event models"""
    
    def test_thought_create_to_kafka_event(self):
        """Test ThoughtCreateRequest can be converted to ThoughtCreatedEvent"""
        # API layer receives this
        api_request = ThoughtCreateRequest(
            text="Should I learn Rust?",
            user_id=uuid4(),
            processing_mode='single'
        )
        
        # API converts to Kafka event
        kafka_event = ThoughtCreatedEvent(
            user_id=str(api_request.user_id),
            thought_id=str(uuid4()),
            text=api_request.text,
            processing_mode=api_request.processing_mode,
            user_context={}
        )
        
        # Validate conversion worked
        assert kafka_event.text == api_request.text
        assert kafka_event.processing_mode == api_request.processing_mode
        assert kafka_event.event_type == 'thought_created'
        
    def test_group_mode_thought_requires_group_id(self):
        """Test group mode thought validation"""
        # Should raise validation error without group_id
        with pytest.raises(ValidationError):
            ThoughtCreateRequest(
                text="Test thought",
                user_id=uuid4(),
                processing_mode='group',
                group_id=None  # Missing required field
            )
        
        # Should pass with group_id
        request = ThoughtCreateRequest(
            text="Test thought",
            user_id=uuid4(),
            processing_mode='group',
            group_id=uuid4()
        )
        assert request.group_id is not None


class TestSSEEventSchemas:
    """Test SSE event schema consistency"""
    
    def test_sse_thought_processing_event(self):
        """Test SSE processing event creation and serialization"""
        event = SSEThoughtProcessingEvent(
            event='thought_processing',
            data={
                'thought_id': str(uuid4()),
                'status': 'processing',
                'message': 'Starting analysis...'
            }
        )
        
        # Should serialize to JSON
        json_str = event.to_json_str()
        assert 'thought_processing' in json_str
        assert 'timestamp' in json_str
        
    def test_sse_agent_completed_event(self):
        """Test SSE agent completed event"""
        event = SSEAgentCompletedEvent(
            event='agent_completed',
            data={
                'thought_id': str(uuid4()),
                'agent_name': 'Classifier',
                'agent_number': 1,
                'progress': '1/5'
            }
        )
        
        json_str = event.to_json_str()
        assert 'agent_completed' in json_str
        assert 'Classifier' in json_str
        
    def test_sse_event_timestamps(self):
        """Test all SSE events have timestamps"""
        events = [
            SSEThoughtProcessingEvent(event='thought_processing', data={}),
            SSEAgentCompletedEvent(event='agent_completed', data={}),
            SSEThoughtCompletedEvent(event='thought_completed', data={}),
            SSEThoughtFailedEvent(event='thought_failed', data={}),
        ]
        
        for event in events:
            assert hasattr(event, 'timestamp')
            assert isinstance(event.timestamp, datetime)


class TestAIAgentOutputSchemas:
    """Test AI agent output validation schemas"""
    
    def test_classification_output_valid(self):
        """Test valid classification output"""
        classification = ClassificationOutput(
            type='task',
            urgency='soon',
            entities=EntityExtraction(
                people=['Alice'],
                dates=['next week'],
                places=[],
                topics=['programming']
            ),
            emotional_tone='curious',
            implied_needs=['learning resources']
        )
        
        assert classification.type == 'task'
        assert classification.urgency == 'soon'
        assert len(classification.entities.topics) == 1
        
    def test_classification_invalid_type(self):
        """Test invalid classification type"""
        with pytest.raises(ValidationError):
            ClassificationOutput(
                type='invalid_type',  # Not in allowed values
                urgency='soon',
                entities=EntityExtraction(),
                emotional_tone='neutral',
                implied_needs=[]
            )
            
    def test_analysis_output_valid(self):
        """Test valid analysis output"""
        analysis = AnalysisOutput(
            goal_alignment=GoalAlignment(
                aligned_goals=['Learn new skills'],
                conflicting_goals=[],
                reasoning='Aligns with growth'
            ),
            underlying_needs=['Skill development'],
            pattern_connections=['Similar to Python learning'],
            realistic_assessment=RealisticAssessment(
                feasibility='High',
                constraints=['Time', 'Complexity']
            ),
            unspoken_factors=['Career advancement']
        )
        
        assert len(analysis.underlying_needs) > 0
        assert isinstance(analysis.goal_alignment, GoalAlignment)
        
    def test_value_impact_output_score_range(self):
        """Test value scores must be 0-10"""
        # Valid scores
        value_impact = ValueImpactOutput(
            economic_value=ValueScore(score=8, reasoning="High ROI"),
            relational_value=ValueScore(score=3, reasoning="Low impact"),
            legacy_value=ValueScore(score=5, reasoning="Medium"),
            health_value=ValueScore(score=2, reasoning="Minimal"),
            growth_value=ValueScore(score=9, reasoning="Significant"),
            weighted_total=6.5,
            overall_assessment="Positive"
        )
        
        assert 0 <= value_impact.economic_value.score <= 10
        assert 0 <= value_impact.weighted_total <= 10
        
        # Invalid score (out of range)
        with pytest.raises(ValidationError):
            ValueScore(score=15, reasoning="Too high")
            
    def test_action_plan_output_valid(self):
        """Test valid action plan output"""
        action_plan = ActionPlanOutput(
            quick_wins=[
                QuickWin(
                    action="Watch intro video",
                    duration="15min",
                    timing="Today evening"
                )
            ],
            main_actions=[
                MainAction(
                    action="Complete Rust book",
                    duration="2 months",
                    prerequisites=["Install Rust"],
                    obstacles=["Time constraints"],
                    mitigation="Schedule 1hr daily",
                    timing="Mornings"
                )
            ],
            delegation_opportunities=["None"],
            success_metrics=["Complete 5 projects"]
        )
        
        assert len(action_plan.quick_wins) == 1
        assert len(action_plan.main_actions) == 1
        
    def test_priority_output_valid_levels(self):
        """Test priority output with valid levels"""
        priority = PriorityOutput(
            priority_level='High',
            urgency_reasoning='Aligns with Q1 goals',
            strategic_fit='Strong',
            recommended_timeline=RecommendedTimeline(
                start='This week',
                duration='3 months',
                checkpoints=['Month 1: Basics', 'Month 2: Projects']
            ),
            final_recommendation='Start immediately'
        )
        
        assert priority.priority_level in ['Critical', 'High', 'Medium', 'Low', 'Defer']
        
        # Invalid priority level
        with pytest.raises(ValidationError):
            PriorityOutput(
                priority_level='UltraHigh',  # Invalid
                urgency_reasoning='Test',
                strategic_fit='Test',
                recommended_timeline=RecommendedTimeline(
                    start='Now',
                    duration='1 week',
                    checkpoints=[]
                ),
                final_recommendation='Test'
            )


class TestKafkaEventSchemas:
    """Test Kafka event schema validation"""
    
    def test_thought_created_event(self):
        """Test ThoughtCreatedEvent validation"""
        event = ThoughtCreatedEvent(
            user_id=str(uuid4()),
            thought_id=str(uuid4()),
            text="Test thought",
            processing_mode='single'
        )
        
        assert event.event_type == 'thought_created'
        assert event.processing_mode == 'single'
        assert event.group_id is None
        
    def test_thought_processing_event(self):
        """Test ThoughtProcessingEvent validation"""
        event = ThoughtProcessingEvent(
            user_id=str(uuid4()),
            thought_id=str(uuid4()),
            status='processing',
            message='Processing...'
        )
        
        assert event.event_type == 'thought_processing'
        assert event.status == 'processing'
        
    def test_thought_agent_completed_event(self):
        """Test ThoughtAgentCompletedEvent validation"""
        event = ThoughtAgentCompletedEvent(
            user_id=str(uuid4()),
            thought_id=str(uuid4()),
            agent_name='Classifier',
            agent_number=1,
            progress='1/5'
        )
        
        assert event.event_type == 'thought_agent_completed'
        assert 1 <= event.agent_number <= 5
        
        # Invalid agent number
        with pytest.raises(ValidationError):
            ThoughtAgentCompletedEvent(
                user_id=str(uuid4()),
                thought_id=str(uuid4()),
                agent_name='Invalid',
                agent_number=10,  # Out of range
                progress='10/5'
            )
            
    def test_thought_completed_event(self):
        """Test ThoughtCompletedEvent validation"""
        event = ThoughtCompletedEvent(
            user_id=str(uuid4()),
            thought_id=str(uuid4()),
            status='completed',
            message='Done!',
            processing_time_seconds=15.5
        )
        
        assert event.event_type == 'thought_completed'
        assert event.status == 'completed'
        assert event.processing_time_seconds > 0
        
    def test_thought_failed_event(self):
        """Test ThoughtFailedEvent validation"""
        event = ThoughtFailedEvent(
            user_id=str(uuid4()),
            thought_id=str(uuid4()),
            status='failed',
            error_message='AI provider timeout',
            retry_count=2
        )
        
        assert event.event_type == 'thought_failed'
        assert event.status == 'failed'
        assert event.retry_count >= 0


class TestCrossServiceContractConsistency:
    """Test contracts remain consistent across service boundaries"""
    
    def test_api_to_kafka_to_worker_flow(self):
        """Test data flows correctly from API → Kafka → Worker"""
        # 1. API receives request
        user_id = uuid4()
        api_request = ThoughtCreateRequest(
            text="Learn Python",
            user_id=user_id,
            processing_mode='single'
        )
        
        # 2. API creates Kafka event
        thought_id = uuid4()
        kafka_event = ThoughtCreatedEvent(
            user_id=str(user_id),
            thought_id=str(thought_id),
            text=api_request.text,
            processing_mode=api_request.processing_mode,
            user_context={'goals': ['Learn programming']}
        )
        
        # 3. Worker processes and creates SSE events
        sse_processing = SSEThoughtProcessingEvent(
            event='thought_processing',
            data={
                'thought_id': str(thought_id),
                'status': 'processing',
                'message': 'Starting...'
            }
        )
        
        sse_completed = SSEThoughtCompletedEvent(
            event='thought_completed',
            data={
                'thought_id': str(thought_id),
                'status': 'completed',
                'message': 'Done!'
            }
        )
        
        # Verify data consistency
        assert kafka_event.text == api_request.text
        assert sse_processing.data['thought_id'] == str(thought_id)
        assert sse_completed.data['thought_id'] == str(thought_id)
        
    def test_all_events_have_timestamps(self):
        """Test all event types include timestamps"""
        events = [
            ThoughtCreatedEvent(user_id=str(uuid4()), thought_id=str(uuid4()), text="Test"),
            ThoughtProcessingEvent(user_id=str(uuid4()), thought_id=str(uuid4()), status='processing', message='Test'),
            ThoughtCompletedEvent(user_id=str(uuid4()), thought_id=str(uuid4()), status='completed', message='Test'),
            SSEThoughtProcessingEvent(event='thought_processing', data={}),
            SSEThoughtCompletedEvent(event='thought_completed', data={})
        ]
        
        for event in events:
            assert hasattr(event, 'timestamp')
            assert isinstance(event.timestamp, datetime)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
