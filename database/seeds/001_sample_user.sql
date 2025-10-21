-- Sample user data for testing
-- Insert a test user with complete context

INSERT INTO users (id, email, context, context_version)
VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'demo@example.com',
    '{
        "demographics": {
            "age": 35,
            "role": "Senior Software Engineer",
            "family": "Married, 2 kids (5, 8)",
            "location": "San Francisco Bay Area"
        },
        "goals": {
            "career": "VP Engineering in 3 years, launch side project",
            "family": "Quality time with kids, strengthen marriage",
            "health": "Run half-marathon, reduce stress",
            "financial": "Save $50k/year, diversify income"
        },
        "constraints": {
            "time": "50hr work weeks, 2hr commute daily",
            "energy": "Morning person, depleted after 8pm",
            "commitments": "Son soccer Saturdays, date night Fridays"
        },
        "values_ranking": {
            "family": 10,
            "health": 9,
            "career": 8,
            "wealth": 7,
            "legacy": 8
        },
        "current_challenges": [
            "Feeling burned out at work",
            "Missing kids milestones",
            "Haven not exercised in 2 weeks"
        ],
        "recent_patterns": {
            "recurring_thoughts": ["career change", "work-life balance"],
            "stress_triggers": ["late meetings", "weekend work"],
            "energy_peaks": ["6-9am", "weekends"]
        }
    }'::jsonb,
    1
);

-- Insert some sample thoughts for testing
INSERT INTO thoughts (user_id, text, status)
VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Should I start learning Rust to stay relevant in my career?', 'pending'),
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Missed my daughter school play today because of a late meeting', 'pending'),
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Idea: Build a side project to automate my daily standup reports', 'pending'),
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Feeling exhausted, maybe I should take a vacation?', 'pending'),
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'The new AI project at work could be a great learning opportunity', 'pending');

-- Print confirmation
DO $$
BEGIN
    RAISE NOTICE 'Sample data inserted successfully!';
    RAISE NOTICE 'Demo user email: demo@example.com';
    RAISE NOTICE 'Demo user ID: a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';
    RAISE NOTICE 'Sample thoughts: 5 pending thoughts created';
END $$;
