/**
 * Mock Data for Frontend Testing
 * Matches API_SCHEMA.md
 */

const MOCK_DATA = {
    user: {
        id: "mock-user-uuid",
        email: "mock@example.com",
        name: "Mock User",
        created_at: new Date().toISOString()
    },

    thoughts: [
        {
            id: "thought-1",
            user_id: "mock-user-uuid",
            text: "Should I learn Rust or Go for my next project?",
            status: "completed",
            created_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
            processed_at: new Date(Date.now() - 86300000).toISOString(),
            classification: {
                type: "question",
                urgency: "soon",
                emotional_tone: "curious"
            },
            analysis: {
                value_score: 8.5
            },
            value_impact: {
                weighted_total: 8.5
            },
            priority: {
                priority_level: "High"
            }
        },
        {
            id: "thought-2",
            user_id: "mock-user-uuid",
            text: "I'm feeling overwhelmed by the number of meetings this week.",
            status: "completed",
            created_at: new Date(Date.now() - 172800000).toISOString(), // 2 days ago
            processed_at: new Date(Date.now() - 172700000).toISOString(),
            classification: {
                type: "problem",
                urgency: "immediate",
                emotional_tone: "anxious"
            },
            analysis: {
                value_score: 7.0
            },
            value_impact: {
                weighted_total: 7.0
            },
            priority: {
                priority_level: "Critical"
            }
        },
        {
            id: "thought-3",
            user_id: "mock-user-uuid",
            text: "Idea: A coffee machine that orders beans automatically.",
            status: "pending",
            created_at: new Date().toISOString(),
            classification: null,
            analysis: null,
            value_impact: null,
            priority: null
        }
    ],

    groups: [
        {
            id: "group-1",
            user_id: "mock-user-uuid",
            name: "Board of Advisors",
            description: "My personal board of directors",
            personas: [
                { id: "p1", name: "Steve Jobs", prompt: "Think like Steve Jobs" },
                { id: "p2", name: "Marcus Aurelius", prompt: "Think like a Stoic" }
            ]
        }
    ],

    synthesis: {
        week_start: "2023-10-23",
        week_end: "2023-10-29",
        synthesis: {
            key_themes: ["Learning new tech", "Productivity"],
            recommendations: ["Block time for deep work", "Start with a small Rust project"]
        }
    }
};
