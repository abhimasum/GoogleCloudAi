"""BigQuery agent: provides metadata index lookups for country, state, and district data.

This agent queries BigQuery tables to find relevant IDs and metadata, which the
orchestrator then uses to provide context for the retriever agent's RAG searches.
"""

import os
from typing import Any

from google.adk.agents import Agent
from google.cloud import bigquery


class BigQueryTool:
    """Tool for querying BigQuery tables."""
    
    def __init__(self):
        self.project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.dataset_id = os.environ.get("BQ_DATASET", "geography_index")
        self.client = bigquery.Client(project=self.project_id)
    
    def search_countries(self, query: str) -> list[dict[str, Any]]:
        """Search for countries matching the query.
        
        Args:
            query: Search term for country name
            
        Returns:
            List of matching countries with id, name, and metadata
        """
        sql = f"""
        SELECT id, name, capital, population, area_km2
        FROM `{self.project_id}.{self.dataset_id}.countries`
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
        results = self.client.query(sql, job_config=job_config).result()
        return [dict(row) for row in results]
    
    def search_states(self, query: str, country_id: int | None = None) -> list[dict[str, Any]]:
        """Search for states matching the query.
        
        Args:
            query: Search term for state name
            country_id: Optional country ID to filter by
            
        Returns:
            List of matching states with id, name, country, and metadata
        """
        where_clauses = ["(LOWER(name) LIKE LOWER(@query) OR LOWER(capital) LIKE LOWER(@query))"]
        if country_id is not None:
            where_clauses.append("country_id = @country_id")
        
        sql = f"""
        SELECT s.id, s.name, s.capital, s.population, s.area_km2, 
               c.name as country_name
        FROM `{self.project_id}.{self.dataset_id}.states` s
        JOIN `{self.project_id}.{self.dataset_id}.countries` c ON s.country_id = c.id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY s.name
        LIMIT 10
        """
        
        params = [bigquery.ScalarQueryParameter("query", "STRING", f"%{query}%")]
        if country_id is not None:
            params.append(bigquery.ScalarQueryParameter("country_id", "INT64", country_id))
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        results = self.client.query(sql, job_config=job_config).result()
        return [dict(row) for row in results]
    
    def search_districts(self, query: str, state_id: int | None = None) -> list[dict[str, Any]]:
        """Search for districts matching the query.
        
        Args:
            query: Search term for district name
            state_id: Optional state ID to filter by
            
        Returns:
            List of matching districts with id, name, state, and metadata
        """
        where_clauses = ["LOWER(d.name) LIKE LOWER(@query)"]
        if state_id is not None:
            where_clauses.append("d.state_id = @state_id")
        
        sql = f"""
        SELECT d.id, d.name, d.headquarters, d.population, d.area_km2,
               s.name as state_name, c.name as country_name
        FROM `{self.project_id}.{self.dataset_id}.districts` d
        JOIN `{self.project_id}.{self.dataset_id}.states` s ON d.state_id = s.id
        JOIN `{self.project_id}.{self.dataset_id}.countries` c ON s.country_id = c.id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY d.name
        LIMIT 20
        """
        
        params = [bigquery.ScalarQueryParameter("query", "STRING", f"%{query}%")]
        if state_id is not None:
            params.append(bigquery.ScalarQueryParameter("state_id", "INT64", state_id))
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        results = self.client.query(sql, job_config=job_config).result()
        return [dict(row) for row in results]


# Initialize the tool
bq_tool = BigQueryTool()

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
    states, and districts.
    
    Your role:
    - Parse user queries to identify geographic entities (country, state, district names)
    - Search BigQuery tables to find matching IDs and metadata
    - Return structured information that helps narrow down RAG searches
    
    Tools available:
    - search_countries(query): Find countries by name or capital
    - search_states(query, country_id): Find states, optionally filtered by country
    - search_districts(query, state_id): Find districts, optionally filtered by state
    
    Always return:
    - Entity IDs (country_id, state_id, district_id)
    - Entity names and hierarchies
    - Key metadata (population, area, capitals, headquarters)
    
    Format your response as structured data that can be easily parsed by the orchestrator.
    """,
    functions=[
        bq_tool.search_countries,
        bq_tool.search_states,
        bq_tool.search_districts,
    ],
)
