"""BigQuery agent: provides metadata index lookups for country, state, and district data.

This agent queries BigQuery tables to find relevant IDs and metadata, which the
orchestrator then uses to provide context for the retriever agent's RAG searches.
"""

import json
import os
from typing import Any

from google.adk.agents import Agent
from google.cloud import bigquery


# Initialize BigQuery client
_project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
_dataset_id = os.environ.get("BQ_DATASET", "geography_index")
_client = bigquery.Client(project=_project_id)


def search_countries(query: str) -> str:
    """Search for countries matching the query.
    
    Args:
        query: Search term for country name or capital
            
    Returns:
        JSON string containing list of matching countries
    """
    try:
        sql = f"""
        SELECT id, name, capital, population, area_km2
        FROM `{_project_id}.{_dataset_id}.countries`
        WHERE LOWER(name) LIKE LOWER(@query)
        OR LOWER(capital) LIKE LOWER(@query)
        ORDER BY name
        LIMIT 10
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("query", "STRING", f"%{query}%")
            ]
        )
        results = _client.query(sql, job_config=job_config).result()
        data = [dict(row) for row in results]
        return json.dumps({"results": data, "count": len(data)})
    except Exception as e:
        return json.dumps({"error": str(e), "results": []})


def search_states(query: str, country_id: int | None = None) -> str:
    """Search for states matching the query.
    
    Args:
        query: Search term for state name
        country_id: Optional country ID to filter by (default: 1 for India)
            
    Returns:
        JSON string containing list of matching states
    """
    try:
        # Default to India (country_id=1) if not specified
        if country_id is None:
            country_id = 1
            
        where_clauses = ["(LOWER(name) LIKE LOWER(@query) OR LOWER(capital) LIKE LOWER(@query))"]
        where_clauses.append("country_id = @country_id")
        
        sql = f"""
        SELECT s.id, s.name, s.capital, s.population, s.area_km2, 
               c.name as country_name
        FROM `{_project_id}.{_dataset_id}.states` s
        JOIN `{_project_id}.{_dataset_id}.countries` c ON s.country_id = c.id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY s.name
        LIMIT 10
        """
        
        params = [
            bigquery.ScalarQueryParameter("query", "STRING", f"%{query}%"),
            bigquery.ScalarQueryParameter("country_id", "INT64", country_id)
        ]
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        results = _client.query(sql, job_config=job_config).result()
        data = [dict(row) for row in results]
        return json.dumps({"results": data, "count": len(data)})
    except Exception as e:
        return json.dumps({"error": str(e), "results": []})


def search_districts(query: str, state_id: int | None = None) -> str:
    """Search for districts matching the query.
    
    Args:
        query: Search term for district name
        state_id: Optional state ID to filter by
            
    Returns:
        JSON string containing list of matching districts
    """
    try:
        where_clauses = ["LOWER(d.name) LIKE LOWER(@query)"]
        params = [bigquery.ScalarQueryParameter("query", "STRING", f"%{query}%")]
        
        if state_id is not None:
            where_clauses.append("d.state_id = @state_id")
            params.append(bigquery.ScalarQueryParameter("state_id", "INT64", state_id))
        
        sql = f"""
        SELECT d.id, d.name, d.headquarters, d.population, d.area_km2,
               s.name as state_name, c.name as country_name
        FROM `{_project_id}.{_dataset_id}.districts` d
        JOIN `{_project_id}.{_dataset_id}.states` s ON d.state_id = s.id
        JOIN `{_project_id}.{_dataset_id}.countries` c ON s.country_id = c.id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY d.name
        LIMIT 20
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        results = _client.query(sql, job_config=job_config).result()
        data = [dict(row) for row in results]
        return json.dumps({"results": data, "count": len(data)})
    except Exception as e:
        return json.dumps({"error": str(e), "results": []})


root_agent = Agent(
    model=os.environ.get("BIGQUERY_MODEL", "gemini-2.5-flash"),
    name="bigquery_agent",
    description=(
        "Specialist agent for querying structured geography metadata from BigQuery. "
        "Provides IDs and indices for countries, states, and districts that can be "
        "used to focus RAG searches in the retriever agent."
    ),
    instruction="""
    You are a BigQuery specialist that helps find structured metadata about countries, 
    states, and districts in India.
    
    Your role:
    - Parse user queries to identify geographic entities (country, state, district names)
    - Search BigQuery tables to find matching IDs and metadata
    - Return structured information that helps narrow down RAG searches
    - Parse JSON responses from search functions and provide context
    
    Tools available:
    - search_countries(query): Find countries by name or capital
    - search_states(query, country_id): Find states, optionally filtered by country (default: India)
    - search_districts(query, state_id): Find districts, optionally filtered by state
    
    All functions return JSON strings with results. Parse them and return:
    - Entity IDs (country_id, state_id, district_id)
    - Entity names and hierarchies
    - Key metadata (population, area, capitals, headquarters)
    
    Example: If asked "What is the capital of Maharashtra?":
    1. Call search_states("Maharashtra") 
    2. Parse result to find state_id and capital
    3. Return: "Maharashtra (state_id: 1) - Capital: Mumbai"
    """,
    functions=[
        search_countries,
        search_states,
        search_districts,
    ],
)
