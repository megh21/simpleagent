import os
import asyncio
from typing import List, Dict, Optional
import uuid
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from document_processor import query_documents
from langchain.schema import SystemMessage, HumanMessage
from web_search import search_duckduckgo, fetch_webpage_content

# Initialize Azure OpenAI LLM
llm = AzureChatOpenAI(
    deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-35-turbo"),
    openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    openai_api_type="azure",
    openai_api_base=os.getenv("AZURE_OPENAI_API_BASE"),
    openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0
)

# Define tools
async def search_documents(query: str, doc_ids: List[str]) -> Dict:
    """Search for information in the document database."""
    results = await query_documents(query, doc_ids)
    return results

class AgentTools:
    def __init__(self, doc_ids: List[str]):
        self.doc_ids = doc_ids
        
    def get_search_tool(self):
        return Tool.from_function(
            func=lambda query: asyncio.run(search_documents(query, self.doc_ids)),
            name="search_documents",
            description="Search for information in the documents. Input should be a search query."
        )
    
    # Add this new tool in the AgentTools class
    def get_web_search_tool(self):
        return Tool.from_function(
            func=lambda query: asyncio.run(search_duckduckgo(query)),
            name="search_web",
            description="Search the internet for information. Input should be a search query."
        )

# Add a new function to create a web search agent
def create_web_search_agent():
    tools = AgentTools([])  # No doc_ids needed for web search
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a web research agent specialized in finding information from the internet.
        Use the search_web tool to find relevant information based on the user's query.
        Be thorough and precise in your research, focusing on finding factual and up-to-date information.
        Always cite your sources when providing information from the web.
        """),
        ("human", "{input}"),
    ])
    
    agent = create_openai_tools_agent(llm, [tools.get_web_search_tool()], prompt)
    return AgentExecutor(agent=agent, tools=[tools.get_web_search_tool()], verbose=True)


def create_research_agent(doc_ids: List[str]):
    tools = AgentTools(doc_ids)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a research agent specialized in finding information from documents.
        Use the search_documents tool to find relevant information based on the user's query.
        Be thorough and precise in your research, focusing on finding the most relevant facts and details.
        """),
        ("human", "{input}"),
        ("ai", "{agent_scratchpad}")  # Add this missing variable
    ])
    
    agent = create_openai_tools_agent(llm, [tools.get_search_tool()], prompt)
    return AgentExecutor(agent=agent, tools=[tools.get_search_tool()], verbose=True)

def create_writing_agent():
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a writing agent specialized in crafting clear, concise, and informative responses.
        Your task is to take information provided by other agents and turn it into a well-structured response.
        Focus on clarity, accuracy, and providing a comprehensive answer to the user's query.
        """),
        ("human", "{input}"),
        ("ai", "{agent_scratchpad}")  # Add this missing variable
    ])
    
    agent = create_openai_tools_agent(llm, [], prompt)
    return AgentExecutor(agent=agent, tools=[], verbose=True)

def create_validation_agent():
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a validation agent specialized in fact-checking and ensuring accuracy.
        Your task is to review information and answers, checking for inconsistencies, gaps, or errors.
        Provide feedback on the completeness and accuracy of the information.
        """),
        ("human", "{input}"),
        ("ai", "{agent_scratchpad}")  # Add this missing variable
    ])
    
    agent = create_openai_tools_agent(llm, [], prompt)
    return AgentExecutor(agent=agent, tools=[], verbose=True)

# Execute agents in parallel
# Update the execute_agents_parallel function to include web search
async def execute_agents_parallel(query: str, doc_ids: Optional[List[str]] = None, include_web_search: bool = False):
    tasks = []
    
    # If document IDs are provided, run document research
    if doc_ids and len(doc_ids) > 0:
        research_agent = create_research_agent(doc_ids)
        research_task = asyncio.create_task(
            research_agent.ainvoke({"input": f"Find information related to: {query}"})
        )
        tasks.append(("document_research", research_task))
    
    # If web search is requested, run web research
    if include_web_search:
        web_agent = create_web_search_agent()
        web_task = asyncio.create_task(
            web_agent.ainvoke({"input": f"Search the web for information about: {query}"})
        )
        tasks.append(("web_research", web_task))
    
    # Execute research tasks
    research_results = {}
    for task_name, task in tasks:
        result = await task
        research_results[task_name] = result.get("output", "No information found.")
    
    # Combine research results
    combined_research = ""
    if "document_research" in research_results:
        combined_research += f"DOCUMENT SOURCES:\n{research_results['document_research']}\n\n"
    if "web_research" in research_results:
        combined_research += f"WEB SOURCES:\n{research_results['web_research']}\n\n"
    
    if not combined_research:
        return {"answer": "No sources available for research. Please select at least one document or enable web search.", "sources": []}
    
    # Execute writing and validation agents
    writing_agent = create_writing_agent()
    validation_agent = create_validation_agent()
    
    writing_task = asyncio.create_task(
        writing_agent.ainvoke({
            "input": f"Create a comprehensive answer to the query: '{query}' based on this information: {combined_research}"
        })
    )
    
    validation_task = asyncio.create_task(
        validation_agent.ainvoke({
            "input": f"Validate this information and check for any inconsistencies or missing details: {combined_research}"
        })
    )
    
    # Wait for both tasks to complete
    writing_result, validation_result = await asyncio.gather(writing_task, validation_task)
    
    # Extract outputs
    answer = writing_result.get("output", "Could not generate an answer.")
    validation = validation_result.get("output", "No validation performed.")
    
    # Extract sources
    sources = []
    
    # Extract document sources
    if "document_research" in research_results:
        doc_output = research_results["document_research"]
        if "results" in doc_output:
            try:
                import json
                results_str = doc_output.split("results")[1].split("]")[0] + "]"
                results_str = "{\"results\"" + results_str
                doc_sources = json.loads(results_str).get("results", [])
                for source in doc_sources:
                    source["type"] = "document"
                    sources.append(source)
            except:
                pass
    
    # Extract web sources
    if "web_research" in research_results:
        web_output = research_results["web_research"]
        if "search results" in web_output.lower():
            try:
                # Try to parse web search results
                import re
                web_sources = []
                results_pattern = r"Title: (.*?)\nSnippet: (.*?)\nLink: (.*?)(?:\n|$)"
                matches = re.findall(results_pattern, web_output, re.DOTALL)
                
                for match in matches:
                    web_sources.append({
                        "title": match[0],
                        "content": match[1],
                        "link": match[2],
                        "type": "web"
                    })
                
                sources.extend(web_sources)
            except:
                pass
    
    return {
        "answer": answer,
        "validation": validation,
        "sources": sources
    }