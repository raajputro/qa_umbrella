def build_scenario_prompt(requirement_text: str) -> str:
    return f"""
You are a senior QA analyst.

Read the following requirement and generate structured test scenarios.

Requirement:
{requirement_text}

Return:
1. Feature name
2. Assumptions
3. Positive scenarios
4. Negative scenarios
5. Boundary scenarios
6. Role/permission scenarios
7. High-risk areas
"""