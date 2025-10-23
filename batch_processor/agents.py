"""
5-Agent processing pipeline for thought analysis
Each agent performs a specific analysis task
"""
import json
from typing import Dict, Any, List
from loguru import logger

from config import settings
from ai_providers import AIProviderFactory
from ai_providers.base import AIMessage


class AgentPipeline:
    """
    5-Agent pipeline for thought processing:
    1. Classification & Extraction
    2. Contextual Analysis
    3. Value Impact Assessment
    4. Action Planning
    5. Prioritization
    """

    def __init__(self):
        self.client = AIProviderFactory.create(
            provider_type=settings.ai_provider,
            api_key=settings.get_ai_api_key(),
            model=settings.get_ai_model()
        )
        self.model = settings.get_ai_model()
        self.max_tokens = settings.max_tokens

    def _create_system_prompt(self, user_context: Dict[str, Any]) -> str:
        """Create system prompt with user context as a string"""
        base_instruction = """You are an AI agent specialized in analyzing personal thoughts.
Your role is to provide deep, contextual analysis based on the user's life circumstances,
goals, constraints, and values. Always be honest, insightful, and actionable."""
        
        user_context_str = f"\n\nUSER CONTEXT:\n{json.dumps(user_context, indent=2)}"
        
        return base_instruction + user_context_str

    async def _generate_json_response(
        self,
        user_prompt: str,
        user_context: Dict[str, Any],
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Helper method to generate JSON responses using the unified AIProvider interface
        
        Args:
            user_prompt: The user's prompt/question
            user_context: User context for system prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Parsed JSON response as dictionary
            
        Raises:
            Exception if generation or parsing fails
        """
        try:
            # Create system prompt
            system_prompt = self._create_system_prompt(user_context)
            
            # Create message in AIMessage format
            messages = [AIMessage(role="user", content=user_prompt)]
            
            # Call unified generate method
            if settings.prompt_cache_enabled and self.client.supports_caching():
                # Use caching if enabled and supported
                response = await self.client.generate_with_cache(
                    messages=messages,
                    system_prompt="""You are an AI agent specialized in analyzing personal thoughts.
Your role is to provide deep, contextual analysis based on the user's life circumstances,
goals, constraints, and values. Always be honest, insightful, and actionable.""",
                    cacheable_context=f"USER CONTEXT:\n{json.dumps(user_context, indent=2)}",
                    max_tokens=max_tokens
                )
            else:
                # Use standard generation
                response = await self.client.generate(
                    messages=messages,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=0.7
                )
            
            # Parse JSON response
            # Strip markdown code blocks if present (Gemini sometimes adds ```json ... ```)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            if content.startswith("```"):
                content = content[3:]  # Remove ```
            if content.endswith("```"):
                content = content[:-3]  # Remove trailing ```
            content = content.strip()
            
            result = json.loads(content)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response content: {response.content[:500]}...")
            return {"error": "Failed to parse JSON", "raw": response.content}
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise

    async def classify(
        self,
        thought_text: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent 1: Classification & Extraction
        Extracts structured information from the thought
        """
        prompt = f"""Analyze this thought and extract structured information:

THOUGHT: "{thought_text}"

Return ONLY a valid JSON object with these exact fields (no additional text):
- type: (task/problem/idea/question/observation/emotion)
- urgency: (immediate/soon/eventually/never)
- entities: {{people: [], dates: [], places: [], topics: []}}
- emotional_tone: (excited/anxious/frustrated/neutral/curious/overwhelmed/hopeful)
- implied_needs: [list of what the person might need]
- complexity: (simple/moderate/complex)

Be specific and context-aware. Consider the user's background. RESPOND WITH ONLY JSON, NO MARKDOWN OR ADDITIONAL TEXT."""

        try:
            result = await self._generate_json_response(prompt, user_context, max_tokens=1000)
            logger.debug(f"Classification complete: {result.get('type')}")
            return result
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            raise

    async def analyze(
        self,
        thought_text: str,
        classification: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent 2: Contextual Analysis
        Provides deep contextual understanding
        """
        prompt = f"""Provide deep contextual analysis of this thought:

THOUGHT: "{thought_text}"
CLASSIFICATION: {json.dumps(classification, indent=2)}

Return ONLY a valid JSON object with these exact fields (no markdown, no additional text):
- goal_alignment: {{aligned_goals: [], conflicting_goals: [], reasoning: ""}}
- underlying_needs: [deeper needs beyond surface thought]
- pattern_connections: [how this relates to user's recent challenges/patterns]
- realistic_assessment: {{feasibility: "", given_constraints: "", time_required: ""}}
- unspoken_factors: [important considerations the user may not have mentioned]
- opportunity_cost: ""

Be honest, insightful, and consider the user's complete context. RESPOND WITH ONLY JSON, NO MARKDOWN OR ADDITIONAL TEXT."""

        try:
            result = await self._generate_json_response(prompt, user_context, max_tokens=1500)
            logger.debug("Contextual analysis complete")
            return result
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise

    async def assess_value(
        self,
        thought_text: str,
        classification: Dict[str, Any],
        analysis: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent 3: Value Impact Assessment
        Evaluates impact across 5 value dimensions
        """
        values_ranking = user_context.get("values_ranking", {})

        prompt = f"""Assess the value impact of pursuing this thought:

THOUGHT: "{thought_text}"
CLASSIFICATION: {json.dumps(classification, indent=2)}
ANALYSIS: {json.dumps(analysis, indent=2)}

USER'S VALUES RANKING: {json.dumps(values_ranking, indent=2)}

Evaluate impact on each dimension (0-10 scale):

Return JSON:
{{
  "economic_value": {{
    "score": <0-10>,
    "reasoning": "",
    "timeframe": "immediate/short-term/long-term",
    "confidence": "low/medium/high"
  }},
  "relational_value": {{
    "score": <0-10>,
    "reasoning": "",
    "affected_relationships": [],
    "confidence": "low/medium/high"
  }},
  "legacy_value": {{
    "score": <0-10>,
    "reasoning": "",
    "long_term_impact": "",
    "confidence": "low/medium/high"
  }},
  "health_value": {{
    "score": <0-10>,
    "reasoning": "",
    "physical_mental": "physical/mental/both",
    "confidence": "low/medium/high"
  }},
  "growth_value": {{
    "score": <0-10>,
    "reasoning": "",
    "learning_areas": [],
    "confidence": "low/medium/high"
  }},
  "weighted_total": <calculated using user's values_ranking>,
  "overall_assessment": ""
}}

Be realistic and consider both positive and negative impacts."""

        try:
            result = await self._generate_json_response(prompt, user_context, max_tokens=2000)
            logger.debug(f"Value assessment complete: weighted_total={result.get('weighted_total')}")
            return result
        except Exception as e:
            logger.error(f"Value assessment failed: {e}")
            raise

    async def plan_actions(
        self,
        thought_text: str,
        analysis: Dict[str, Any],
        value_impact: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent 4: Action Planning
        Creates specific, realistic action steps
        """
        constraints = user_context.get("constraints", {})
        recent_patterns = user_context.get("recent_patterns", {})
        energy_peaks = recent_patterns.get("energy_peaks", []) if isinstance(recent_patterns, dict) else []

        prompt = f"""Create a realistic action plan for this thought:

THOUGHT: "{thought_text}"
ANALYSIS: {json.dumps(analysis, indent=2)}
VALUE IMPACT: {json.dumps(value_impact, indent=2)}

USER CONSTRAINTS: {json.dumps(constraints, indent=2)}
ENERGY PEAKS: {energy_peaks}

Return JSON:
{{
  "quick_wins": [
    {{
      "action": "",
      "duration": "<30min",
      "timing": "when to do this",
      "outcome": "expected result"
    }}
  ],
  "main_actions": [
    {{
      "action": "",
      "duration": "",
      "prerequisites": [],
      "obstacles": [],
      "mitigation": "",
      "timing": "best time based on energy patterns"
    }}
  ],
  "delegation_opportunities": [
    {{
      "task": "",
      "who": "who could help",
      "why": "benefit of delegating"
    }}
  ],
  "avoid": ["things NOT to do and why"],
  "success_metrics": ["how to know it's working"]
}}

Be specific and actionable. Consider the user's time and energy constraints."""

        try:
            result = await self._generate_json_response(prompt, user_context, max_tokens=2000)
            logger.debug(f"Action planning complete: {len(result.get('main_actions', []))} actions")
            return result
        except Exception as e:
            logger.error(f"Action planning failed: {e}")
            raise

    async def prioritize(
        self,
        thought_text: str,
        action_plan: Dict[str, Any],
        value_impact: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent 5: Prioritization
        Determines priority level and timing
        """
        current_challenges = user_context.get("current_challenges", [])

        prompt = f"""Determine the priority for this thought:

THOUGHT: "{thought_text}"
ACTION PLAN: {json.dumps(action_plan, indent=2)}
VALUE IMPACT: {json.dumps(value_impact, indent=2)}

CURRENT CHALLENGES: {json.dumps(current_challenges, indent=2)}

Return JSON:
{{
  "priority_level": "Critical/High/Medium/Low/Defer",
  "urgency_reasoning": "",
  "strategic_fit": "how this fits user's goals",
  "momentum_impact": "will this create positive momentum?",
  "recommended_timeline": {{
    "start": "when to start",
    "duration": "how long to complete",
    "checkpoints": ["milestones to track"]
  }},
  "dependencies": ["what needs to happen first"],
  "risk_assessment": "what could go wrong",
  "confidence": "low/medium/high",
  "final_recommendation": "clear next step"
}}

Critical: Addresses urgent challenge or high-value opportunity
High: Important for goals, start this week
Medium: Valuable, schedule within month
Low: Nice to have, no rush
Defer: Not aligned with current priorities

RESPOND WITH ONLY JSON, NO MARKDOWN OR ADDITIONAL TEXT."""

        try:
            result = await self._generate_json_response(prompt, user_context, max_tokens=1500)
            logger.debug(f"Prioritization complete: {result.get('priority_level')}")
            return result
        except Exception as e:
            logger.error(f"Prioritization failed: {e}")
            raise

    async def process_thought(
        self,
        thought_text: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the complete 5-agent pipeline
        """
        logger.info(f"Starting 5-agent pipeline for thought: {thought_text[:50]}...")

        try:
            # Agent 1: Classification
            classification = await self.classify(thought_text, user_context)
            logger.debug(f"Classification type: {type(classification)}, value: {str(classification)[:100]}")

            # Agent 2: Analysis
            analysis = await self.analyze(thought_text, classification, user_context)
            logger.debug(f"Analysis type: {type(analysis)}, value: {str(analysis)[:100]}")
            
            # Check if analysis has an error
            if "error" in analysis:
                raise ValueError(f"Analysis failed: {analysis.get('error')}")

            # Agent 3: Value Impact
            value_impact = await self.assess_value(
                thought_text, classification, analysis, user_context
            )

            # Agent 4: Action Planning
            action_plan = await self.plan_actions(
                thought_text, analysis, value_impact, user_context
            )

            # Agent 5: Prioritization
            priority = await self.prioritize(
                thought_text, action_plan, value_impact, user_context
            )

            result = {
                "classification": classification,
                "analysis": analysis,
                "value_impact": value_impact,
                "action_plan": action_plan,
                "priority": priority
            }

            logger.info("5-agent pipeline completed successfully")
            return result

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def process_thought_with_group(
        self,
        thought_text: str,
        user_context: Dict[str, Any],
        personas: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process a thought through multiple personas in parallel

        Args:
            thought_text: The thought to analyze
            user_context: Base user context (shared across all personas)
            personas: List of persona dicts with 'id', 'name', 'prompt' fields

        Returns:
            Dict with:
                - persona_outputs: List of individual persona results
                - consolidated: AI-synthesized consolidated feedback
        """
        import asyncio
        import time

        try:
            logger.info(f"Starting group processing with {len(personas)} personas")
            
            # Process all personas in parallel
            tasks = []
            persona_metadata = []
            
            for persona in personas:
                # Create persona-specific context by injecting persona prompt
                persona_context = {
                    **user_context,
                    "persona_role": persona['prompt'],
                    "persona_name": persona['name']
                }
                
                # Create task for this persona
                task = self.process_thought(thought_text, persona_context)
                tasks.append(task)
                persona_metadata.append({
                    'id': persona['id'],
                    'name': persona['name'],
                    'prompt': persona['prompt']
                })
            
            # Execute all personas in parallel
            start_time = time.time()
            persona_results = await asyncio.gather(*tasks, return_exceptions=True)
            parallel_time = time.time() - start_time
            
            logger.info(f"Parallel persona processing completed in {parallel_time:.2f}s")
            
            # Build persona outputs list (handling any errors)
            persona_outputs = []
            for idx, result in enumerate(persona_results):
                persona_meta = persona_metadata[idx]
                
                if isinstance(result, Exception):
                    logger.error(f"Persona {persona_meta['name']} failed: {result}")
                    persona_outputs.append({
                        'persona_id': persona_meta['id'],
                        'persona_name': persona_meta['name'],
                        'error': str(result),
                        'output': None
                    })
                else:
                    persona_outputs.append({
                        'persona_id': persona_meta['id'],
                        'persona_name': persona_meta['name'],
                        'output': result,
                        'error': None
                    })
            
            # Consolidate outputs using AI
            successful_outputs = [p for p in persona_outputs if p['error'] is None]
            
            if not successful_outputs:
                raise ValueError("All personas failed to process the thought")
            
            consolidated = await self.consolidate_persona_outputs(
                thought_text,
                successful_outputs,
                user_context
            )
            
            return {
                "mode": "group",
                "persona_count": len(personas),
                "persona_outputs": persona_outputs,
                "consolidated": consolidated,
                "processing_time_seconds": parallel_time
            }

        except Exception as e:
            logger.error(f"Group processing failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def consolidate_persona_outputs(
        self,
        thought_text: str,
        persona_outputs: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent 6: Consolidation Agent
        Synthesizes multiple persona perspectives into unified feedback

        Args:
            thought_text: Original thought
            persona_outputs: List of successful persona outputs
            user_context: User context for additional context

        Returns:
            Consolidated analysis with consensus, divergent views, and balanced recommendation
        """
        try:
            logger.info(f"Consolidating {len(persona_outputs)} persona perspectives")
            
            # Format persona outputs for prompt
            formatted_outputs = []
            for p in persona_outputs:
                formatted_outputs.append(f"""
PERSONA: {p['persona_name']}
PRIORITY: {p['output'].get('priority', {}).get('priority_level', 'N/A')}
RECOMMENDATION: {p['output'].get('priority', {}).get('final_recommendation', 'N/A')}
ACTION PLAN: {json.dumps(p['output'].get('action_plan', {}), indent=2)}
VALUE ASSESSMENT: {json.dumps(p['output'].get('value_impact', {}), indent=2)}
""")
            
            prompt = f"""You are a meta-analyst synthesizing multiple perspectives on a single thought.

ORIGINAL THOUGHT: "{thought_text}"

PERSONA FEEDBACK:
{''.join(formatted_outputs)}

Your task: Provide a balanced, synthesized analysis that:
1. Identifies where personas AGREE (consensus points)
2. Highlights where personas DISAGREE (divergent views with reasoning)
3. Provides a BALANCED RECOMMENDATION that integrates all perspectives
4. Attributes key insights to specific personas

Return ONLY valid JSON with this exact structure:
{{
  "consensus_points": [
    "Clear statement of agreement across personas"
  ],
  "divergent_views": {{
    "category_name": {{
      "viewpoint_1": ["Persona Name - their view"],
      "viewpoint_2": ["Persona Name - their view"]
    }}
  }},
  "balanced_recommendation": {{
    "action": "Clear next step that integrates perspectives",
    "reasoning": "Why this balances all viewpoints",
    "next_steps": [
      "Specific actionable step with persona attribution"
    ],
    "timeline": "Recommended timeline considering all inputs"
  }},
  "personas_referenced": {{
    "persona_name": "Key contribution from this persona"
  }},
  "overall_priority": "Critical/High/Medium/Low/Defer",
  "synthesis_confidence": "high/medium/low"
}}

Be objective, fair, and ensure all persona perspectives are represented. RESPOND WITH ONLY JSON."""

            result = await self._generate_json_response(prompt, user_context, max_tokens=2000)
            logger.debug("Consolidation complete")
            return result

        except Exception as e:
            logger.error(f"Consolidation failed: {e}")
            raise
