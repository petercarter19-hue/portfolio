# Portfolio AI Assistant — Requirements

## Purpose
The Portfolio Assistant helps recruiters, hiring managers, and professional
contacts learn about Pete Carter's approved professional experience, education,
projects, skills, accomplishments, and career direction. It answers only from
approved portfolio sources and does not disclose confidential, proprietary,
classified, or sensitive personal information.

## Intended Users
- Recruiters
- Hiring managers
- Engineering leaders
- Professional contacts

## Supported Topics
- Career history
- Systems engineering experience
- MBSE experience
- Requirements and architecture
- Integration and verification
- Leadership
- Education and certifications
- Software and AI learning
- Portfolio projects
- Career objectives
- Public personal interests (in moderation)

## Unsupported Topics
- Classified or proprietary work
- Internal employer information
- Political opinions
- Medical or financial information
- Private family information
- Home address, phone, or personal security information
- General homework or programming help
- Questions unrelated to Pete
- Any claim not contained in the approved knowledge files

## MVP 0 Requirements (Visual Prototype — No AI Yet)
- The chatbot shall appear as a button on the portfolio website
- The chatbot shall open and close without reloading the page
- The chatbot shall display an introductory welcome message
- The chatbot shall display example recruiter questions
- The chatbot shall allow a visitor to enter a question
- The chatbot shall display a temporary sample response
- The chatbot shall work on desktop and mobile screens
- The chatbot shall be usable with a keyboard

## Future Requirements (MVP 1+)
- The assistant shall answer only from approved knowledge files
- The assistant shall not invent experience or qualifications
- The assistant shall identify which source it used for an answer
- The assistant shall refuse questions outside its approved scope
- The API key shall remain on the Flask server — never in the browser
- The website shall apply rate limiting before public deployment

## Initial Example Questions the Assistant Must Answer
1. What systems engineering experience does Pete have?
2. What is Pete's MBSE experience?
3. Has Pete worked with requirements and verification?
4. What leadership experience does Pete have?
5. What software and AI projects is Pete developing?
6. What measurable results has Pete achieved?
7. What roles would Pete be a strong candidate for?
8. What certifications does Pete hold?
9. Where is Pete located?
10. What is Pete currently studying?