from dataclasses import dataclass
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext

from ticket_triage_agent.models import IncomingTicket, TicketResolution
from ticket_triage_agent.knowledge_base import KnowledgeBase

load_dotenv()  # Load environment variables from .env file

@dataclass
class TicketDeps:
    kb: KnowledgeBase
    customers: dict
    known_issues: list[dict]


agent: Agent[TicketDeps, TicketResolution] = Agent(
    "anthropic:claude-sonnet-4-5",
    deps_type=TicketDeps,
    output_type=TicketResolution,
    system_prompt=(
        "You are a support ticket triage assistant. For every ticket, use the "
        "available tools to gather context: search the knowledge base for relevant "
        "help articles, check the customer's account status, and check for known "
        "active issues that might explain the problem. Base your triage decision "
        "and any suggested response only on what the tools return — do not invent "
        "information not found in the tool results."
    )
)

@agent.tool
async def search_kb(ctx: RunContext[TicketDeps], query: str) -> str:
    """
    Search the knowledge base for articles relevant to the customer's issue.
    
    Args:
        ctx (RunContext[TicketDeps]): The run context containing dependencies.
        query (str): The search query.
        
    Returns:
        str: A formatted string of relevant knowledge base articles.
    """
    results = ctx.deps.kb.search(query, top_k=2)
    if not results:
        return "No relevant knowledge base articles found."
    
    return "\n\n".join(f"[Relevance: {score:.2f}] {chunk}" for chunk, score in results)


@agent.tool
async def check_account_status(ctx: RunContext[TicketDeps], customer_id: str) -> str:
    """
    Look up a customer's account status, plan, and ticket history.
    
    Args:
        ctx (RunContext[TicketDeps]): The run context containing dependencies.
        customer_id (str): The ID of the customer.
        
    Returns:
        str: A formatted string describing the customer's account status.
    """
    customer = ctx.deps.customers.get(customer_id)
    if not customer:
        return f"No account information found for customer ID {customer_id}."
    
    return (
        f"Customer Name: {customer['name']}\n"
        f"Plan: {customer['plan']}\n"
        f"Account Status: {customer['account_status']}\n"
        f"Past Tickets: {customer['past_tickets']}"
    )

@agent.tool
async def check_known_issues(ctx: RunContext[TicketDeps], keywords: str) -> str:
    """
    Check for any known active issues that might be affecting customers.
    
    Args:
        ctx (RunContext[TicketDeps]): The run context containing dependencies.
        keywords (str): A string of keywords to search for in the issue descriptions.


    Returns:
        str: A formatted string of known active issues, or a message indicating no issues.
    """
    matches = [
        issue for issue in ctx.deps.known_issues
        if any(word.lower() in issue["description"].lower() for word in keywords.split())
    ]
    if not matches:
        return "No matching known issues found."
    return "\n".join(f"{i['issue_id']}: {i['description']} (status: {i['status']})" for i in matches)


async def triage_ticket(ticket: IncomingTicket, deps: TicketDeps) -> TicketResolution:
    """
    Triage an incoming support ticket using the agent and available tools.
    
    Args:
        ticket (IncomingTicket): The incoming support ticket data.
        deps (TicketDeps): The dependencies required for triage.
        
    Returns:
        TicketResolution: The triage result and suggested response.
    """
    prompt = (
        f"Ticket ID: {ticket.ticket_id}\n"
        f"Customer ID: {ticket.customer_id}\n"
        f"Subject: {ticket.subject}\n"
        f"Body: {ticket.body}\n\n"
        "Please triage this ticket and provide a suggested response."
    )
    result = await agent.run(prompt, deps=deps)
    return result.output