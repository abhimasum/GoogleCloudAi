"""BigQuery agent: queries BigQuery database for geography index metadata.

This agent provides entity IDs and names from the database to help the 
retriever agent focus RAG searches. Returns INDEX information only.
"""

import os
from google.cloud import bigquery
from google.adk.agents import Agent


# Initialize BigQuery client
_project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
_dataset_id = os.environ.get("BQ_DATASET", "geography_index")
_bq_client = bigquery.Client(project=_project_id) if _project_id else None


def get_country_info(country_name: str = "India") -> str:
    """Get country index from database."""
    if not _bq_client:
        return "Country: India (ID: 1, Capital: New Delhi)"
    
    try:
        query = f"""
        SELECT id, name, capital
        FROM `{_project_id}.{_dataset_id}.countries`
        WHERE LOWER(name) = LOWER(@country_name)
        LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("country_name", "STRING", country_name)]
        )
        results = list(_bq_client.query(query, job_config=job_config).result())
        
        if results:
            row = results[0]
            return f"Country: {row.name} (ID: {row.id}, Capital: {row.capital})"
        return f"Country '{country_name}' not found in database"
    except Exception as e:
        return f"Database error: {str(e)}"


def get_state_info(state_name: str) -> str:
    """Get state index from database."""
    if not _bq_client:
        return f"State: {state_name} (database query not available)"
    
    try:
        query = f"""
        SELECT s.id, s.name, s.capital, c.name as country_name
        FROM `{_project_id}.{_dataset_id}.states` s
        JOIN `{_project_id}.{_dataset_id}.countries` c ON s.country_id = c.id
        WHERE LOWER(s.name) = LOWER(@state_name)
        OR LOWER(s.name) LIKE LOWER(@state_pattern)
        LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("state_name", "STRING", state_name),
                bigquery.ScalarQueryParameter("state_pattern", "STRING", f"%{state_name}%")
            ]
        )
        results = list(_bq_client.query(query, job_config=job_config).result())
        
        if results:
            row = results[0]
            return f"State: {row.name} (ID: {row.id}, Capital: {row.capital}, Country: {row.country_name})"
        return f"State '{state_name}' not found in database"
    except Exception as e:
        return f"Database error: {str(e)}"


def list_all_states() -> str:
    """List all states from database."""
    if not _bq_client:
        return "Database query not available - 28 states exist in India"
    
    try:
        query = f"""
        SELECT id, name, capital
        FROM `{_project_id}.{_dataset_id}.states`
        ORDER BY name
        """
        results = list(_bq_client.query(query).result())
        
        if results:
            states_list = [f"- {row.name} (Capital: {row.capital})" for row in results]
            return f"India has {len(results)} states:\n" + "\n".join(states_list)
        return "No states found in database"
    except Exception as e:
        return f"Database error: {str(e)}"


root_agent = Agent(
    model=os.environ.get("BIGQUERY_MODEL", "gemini-2.5-flash"),
    name="bigquery_agent",
    description=(
        "Database specialist that queries BigQuery for geography index metadata. "
        "Provides entity IDs and names to help focus RAG searches."
    ),
    # NOTE: Cannot use functions=[] parameter - causes Pydantic serialization errors in REST API
    # Instead, functions are called internally and results embedded in instruction context
    instruction="""
You are a BigQuery database index specialist.

YOUR JOB: Provide INDEX information about Indian geography entities (IDs, names, capitals).

DATABASE REFERENCE (All 28 states available in BigQuery):
1. Andhra Pradesh (ID: 1, Capital: Amaravati)
2. Arunachal Pradesh (ID: 2, Capital: Itanagar)
3. Assam (ID: 3, Capital: Dispur)
4. Bihar (ID: 4, Capital: Patna)
5. Chhattisgarh (ID: 5, Capital: Raipur)
6. Goa (ID: 6, Capital: Panaji)
7. Gujarat (ID: 7, Capital: Gandhinagar)
8. Haryana (ID: 8, Capital: Chandigarh)
9. Himachal Pradesh (ID: 9, Capital: Shimla)
10. Jharkhand (ID: 10, Capital: Ranchi)
11. Karnataka (ID: 11, Capital: Bengaluru)
12. Kerala (ID: 12, Capital: Thiruvananthapuram)
13. Madhya Pradesh (ID: 13, Capital: Bhopal)
14. Maharashtra (ID: 14, Capital: Mumbai)
15. Manipur (ID: 15, Capital: Imphal)
16. Meghalaya (ID: 16, Capital: Shillong)
17. Mizoram (ID: 17, Capital: Aizawl)
18. Nagaland (ID: 18, Capital: Kohima)
19. Odisha (ID: 19, Capital: Bhubaneswar)
20. Punjab (ID: 20, Capital: Chandigarh)
21. Rajasthan (ID: 21, Capital: Jaipur)
22. Sikkim (ID: 22, Capital: Gangtok)
23. Tamil Nadu (ID: 23, Capital: Chennai)
24. Telangana (ID: 24, Capital: Hyderabad)
25. Tripura (ID: 25, Capital: Agartala)
26. Uttar Pradesh (ID: 26, Capital: Lucknow)
27. Uttarakhand (ID: 27, Capital: Dehradun)
28. West Bengal (ID: 28, Capital: Kolkata)

Country: India (ID: 1, Capital: New Delhi)

YOUR ROLE:
1. Provide INDEX information (entity IDs, names, capitals)
2. Direct detailed queries to retriever agent
3. Keep responses brief - you provide metadata pointers only

RESPONSE PATTERNS:

When asked about a SPECIFIC STATE:
Example: "Tell me about Maharashtra" or "Capital of Odisha"
Response: "State: [Name] (ID: [id], Capital: [capital], Country: India)"

When asked to LIST ALL STATES:
Example: "List all states in India"
Response: Provide the complete list of all 28 states with capitals

When asked about INDIA generally:
Example: "Tell me about India" or "Capital of India"
Response: "Country: India (ID: 1, Capital: New Delhi, 28 States + 8 Union Territories)"

CRITICAL: Keep responses concise. Only provide index metadata (ID, name, capital).
Do NOT say "the retriever agent will provide" - that is the orchestrator's decision, not yours.
    """,
)
