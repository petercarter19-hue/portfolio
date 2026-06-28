# Chatbot Requirements

## Purpose

This chatbot is an AI-powered assistant embedded in Pete Carter's professional
portfolio website. It exists to answer questions from recruiters, hiring managers,
and other professional visitors about Pete's background, experience, skills,
certifications, and career direction.

The chatbot is not a general-purpose assistant. It answers only from an approved
set of career and portfolio information. It does not answer personal, off-topic,
or inappropriate questions.

---

## Intended Users

- Recruiters screening Pete for open positions
- Hiring managers evaluating Pete's fit for a role
- Technical interviewers researching his engineering background
- Colleagues or collaborators exploring his experience
- Anyone visiting the portfolio site with professional interest

---

## What the Chatbot Supports

The chatbot MAY answer questions about:

- Pete's career history and work experience
- Job titles, responsibilities, and employer names (publicly known)
- Technical skills, tools, and methods (Cameo, DOORS, Jira, SysML, Python, Flask, etc.)
- Education degrees, certifications, and professional credentials
- Awards and professional recognition
- Career goals, target roles, and professional direction
- General work location (Athens, Alabama / Huntsville area)
- Hobbies and personal interests Pete has approved for sharing
- Projects built for this portfolio website
- AI and software skills currently in development

---

## What the Chatbot Does NOT Support

The chatbot MUST NEVER answer questions about:

- Classified or controlled information of any kind
- Proprietary employer documents, internal processes, or internal systems
- Specific classified program names, contract numbers, or customer names
- Export-controlled technical data (ITAR/EAR restricted content)
- Security clearance details beyond "holds an active U.S. Secret clearance"
- Colleagues' personal information or identities
- Pete's home address, phone number, or date of birth
- Financial or medical information
- Anything not explicitly approved in the knowledge base

If asked about a prohibited topic, the chatbot should politely decline and
redirect the visitor to the contact form.

---

## MVP 0 Requirements (Visual Prototype — No AI)

MVP 0 is the first stage. The goal is a fully styled, interactive-looking chat
widget with mock (fake) responses. No real AI is connected yet.

### Must Have
- Floating chat button in the bottom-right corner of every page
- Chat panel that opens and closes when the button is clicked
- A welcome message displayed when the chat opens
- User can type a message and press Send or hit Enter
- A mock response appears after a short delay
- The conversation scrolls as messages are added
- Visually consistent with the site's navy/gold color scheme
- Works on both desktop and mobile

### Not Required in MVP 0
- Real AI responses
- Connection to Claude API
- Knowledge base retrieval
- Logging or database
- User authentication

---

## MVP 1 Requirements (Real AI — Claude API)

### Must Have
- Flask /api/chat route that receives user messages
- Integration with Anthropic Claude API
- Knowledge base files loaded and passed as context
- Responses generated from approved knowledge base only
- API key stored in .env file (never in code or JavaScript)
- Basic error handling if the API call fails
- Server-side logging of questions and responses (no PII)

---

## MVP 2 Requirements (RAG — Smarter Retrieval)

### Must Have
- Knowledge base split into smaller chunks
- Relevant chunks retrieved based on the user's question
- Only the most relevant context sent to Claude (reduces cost and improves accuracy)
- Source tracking so responses can cite which file they came from

---

## MVP 3 Requirements (Security and Public Release)

### Must Have
- Rate limiting (limit how many questions one visitor can ask per hour)
- Prompt injection protection
- Refusal for off-topic, abusive, or manipulation attempts
- No classified, proprietary, or export-controlled content anywhere in the knowledge base
- Admin dashboard to view conversation logs
- Reviewed and approved before sharing with real recruiters

---

## Example Recruiter Questions (10 Initial Test Cases)

These are the questions the chatbot should be able to answer well. They will be
used to test the chatbot at each MVP stage.

1. What kind of roles is Pete targeting?
2. Does Pete have a security clearance?
3. What is Pete's MBSE experience?
4. What systems engineering tools has Pete used?
5. What certifications does Pete hold?
6. Has Pete led a team before?
7. What industries is Pete open to?
8. What programming languages does Pete know?
9. What is Pete's educational background?
10. What awards or recognition has Pete received?

---

## Notes

- The chatbot is also a portfolio project demonstrating AI integration skills.
- It should be clearly labeled as an AI assistant, not a human.
- Responses should cite the source (e.g., "Based on Pete's career history...").
- If the chatbot cannot answer something, it should say so honestly and direct
  the visitor to use the contact form to reach Pete directly.
