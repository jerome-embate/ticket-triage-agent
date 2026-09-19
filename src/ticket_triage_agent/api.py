from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ticket_triage_agent.agent import TicketDeps, triage_ticket as run_triage
from ticket_triage_agent.knowledge_base import KnowledgeBase
from ticket_triage_agent.models import IncomingTicket, TicketCategory, TicketResolution, TriageResult, UrgencyLevel
from ticket_triage_agent.seed_data import kb_articles, fake_customers, known_issues

app = FastAPI(title="Ticket Triage Agent API", version="1.0.0")

kb = KnowledgeBase()  # Initialize your knowledge base here
kb.add_article(kb_articles)  # Add your knowledge base articles here
deps = TicketDeps(kb=kb, customers=fake_customers, known_issues=known_issues)  # Initialize dependencies for the agent

@app.post("/triage_ticket")
async def triage_ticket(ticket: IncomingTicket) -> TicketResolution:
    """
    Endpoint to triage an incoming support ticket.
    
    Args:
        ticket (IncomingTicket): The incoming support ticket data.
        
    Returns:
        TicketResolution: The triage result and suggested response.
    """
    try:
        return await run_triage(ticket, deps)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))