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
    functions=[get_country_info, get_state_info, list_all_states],
    instruction="""
You are a BigQuery database index specialist.

YOUR JOB: Query the database and return INDEX information (entity IDs, names, capitals).

AVAILABLE FUNCTIONS:
- get_country_info(country_name) - Returns country ID and basic info
- get_state_info(state_name) - Returns state ID, name, capital, country
- list_all_states() - Returns complete list of all states

RULES:
1. ALWAYS use database functions to get index information
2. Return entity IDs and names to help focus RAG searches
3. For detailed content (culture, economy, history), say:
   "For detailed information, the retriever agent will provide content from documents."
4. Keep responses brief - you provide index pointers only

EXAMPLES:

User asks: "What is the culture of Maharashtra?"
Your response: Use get_state_info("Maharashtra")
Return: "State: Maharashtra (ID: 14, Capital: Mumbai, Country: India).
For detailed cultural information, the retriever agent will provide content from documents."

User asks: "List all states in India"
Your response: Use list_all_states()
Return the complete list from database

User asks: "Tell me about Odisha"  
Your response: Use get_state_info("Odisha")
Return: "State: Odisha (ID: 19, Capital: Bhubaneswar, Country: India).
For detailed information, the retriever agent will provide content from documents."

User asks: "Culture of India"
Your response: Use get_country_info("India")
Return: "Country: India (ID: 1, Capital: New Delhi).
For detailed cultural information, the retriever agent will provide content from documents."
    """,
)
