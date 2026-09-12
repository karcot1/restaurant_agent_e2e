# reservation_agent/a2a_config.py
from a2a.types import AgentSkill
from vertexai.preview.reasoning_engines.templates.a2a import create_agent_card

reservation_skill = AgentSkill(
    id="manage_reservations",
    name="Restaurant Reservations",
    description="Create, check, and cancel table reservations at Foodie Finds restaurant",
    tags=["reservations", "restaurant", "booking"],
    examples=[
        "Book a table for 4 on Friday at 7pm",
        "Check reservation for 555-0101",
        "Cancel my reservation, phone number 555-0101",
    ],
    input_modes=["text/plain"],
    output_modes=["text/plain"],
)

agent_card = create_agent_card(
    agent_name="Reservation Agent",
    description="Handles restaurant table reservations — create, check, and cancel bookings for Foodie Finds restaurant.",
    skills=[reservation_skill],
)