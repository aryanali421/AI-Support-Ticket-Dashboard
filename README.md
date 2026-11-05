# Night Desk – AI Support Ticket Triage

**Less queue chaos. More thoughtful support.**

Night Desk is an AI-assisted support triage workspace. A user submits a complaint, the application analyzes and classifies it, estimates the customer's frustration level, and drafts a possible response. A human reviews and edits the response before sending it.

## Core workflow

1. **Submit a complaint** – Paste a customer complaint into the application.
2. **Load sample tickets** – Use the sample-ticket option to explore the interface with example complaints.
3. **Analyze the ticket** – Generate a category or classification, priority/triage assessment, and an estimate of the customer's frustration.
4. **Draft a response** – Generate a suggested customer-support reply.
5. **Review and export** – Edit the response as needed and download the ticket data as a CSV.

## Human-in-the-loop design

Night Desk is designed to assist support staff, not send messages autonomously. The support agent remains responsible for checking the classification, urgency, tone, and proposed reply before communicating with the customer.

## Data handling

The interface states that tickets live in the current session only. Download the CSV before closing the tab if you need to keep a copy. Session-only data may be lost when the session ends or resets.

## Important notes

- Frustration scores and ticket classifications are AI-generated estimates, not objective measurements.
- Review urgent, safety-related, legal, or account-security complaints carefully and escalate them through the appropriate support process.
- Avoid entering sensitive customer information unless the deployment's privacy and security arrangements permit it.

## Technology

Update this section with the exact framework, AI provider/model, and dependencies used by the implementation. The supplied interface is a Streamlit application.

## Author

Aryan Ali
