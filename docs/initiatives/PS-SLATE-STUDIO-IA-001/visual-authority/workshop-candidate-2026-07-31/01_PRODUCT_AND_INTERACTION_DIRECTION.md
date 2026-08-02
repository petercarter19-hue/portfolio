# Workshop product and interaction direction

## Product thesis

Workshop is one authenticated, private, AI-centric PeerSlate surface where a member can add, strengthen, review, and control information about themselves through small, useful pieces of work.

It is not a whiteboard, journal, résumé-template builder, goal system, public page, generic chatbot, or new platform of connected workspaces.

## One surface, two seamless modes

### Work on Something

The active AI-assisted mode for adding or improving one useful thing.

Core starts:

- create or improve a bullet;
- add or improve a skill;
- add something about work;
- add something personal;
- receive one optional Spark;
- continue unfinished work;
- type or speak an open-ended starting thought.

### My Information

The member-controlled library inside the same Workshop surface.

It supports:

- search;
- Work, Personal, and Both lenses;
- Confirmed, Suggested, Unfinished, and Archived states;
- direct entry and editing;
- source and provenance review;
- AI-use permission;
- current-use review;
- archive and delete;
- clearly unconfirmed suggestions.

My Information is not Settings, a second truth store, a separate public product, or a claim to expose operational account/security data.

## Member mental model

The product must keep these classes distinct:

1. **Member source:** the member's original words, voice, or entered material.
2. **PeerSlate interpretation or suggestion:** AI-proposed wording, classification, connection, or possible addition.
3. **Confirmed private information:** information the member has reviewed and chosen to save privately.
4. **Purpose-specific use:** a separate résumé, Feed, or public-profile draft created only after explicit member action.

The model is:

`Contribute → review → confirm privately → optionally create a separate use`

It is never:

`AI infers → silently saves → silently publishes`

## Five-screen workflow

### 1. Workshop opening

The member sees one grounded, personalized Spark, a direct Type/Speak entry, four compact starting paths, and unfinished work.

The Spark must say what confirmed information prompted it. Spark is the suggestion, not the name or personality of the AI.

Trigger to Screen 2: select `Work on this`, choose a direct starting path, or submit an open thought.

### 2. Type/Speak work session

The member answers one focused question through voice or text. Relevant confirmed information is offered with `Use as context`.

`Use as context` affects only the current private session. It does not confirm, edit, or reclassify the underlying item.

The member may edit directly, save unfinished, stop, or select `Review what I shared`.

Trigger to Screen 3: select `Review what I shared`.

### 3. AI Review

PeerSlate preserves the original wording and separately shows:

- its interpretation;
- what is already strong;
- one standout piece of evidence;
- one thing worth strengthening;
- one focused follow-up question.

This borrows the satisfying contribute/review/improve rhythm of Interview Studio, but it does not grade the person, declare them right or wrong, or score completeness.

The star identifies especially useful evidence. It is not a reward or performance score.

The member may answer, improve with AI, edit directly, save unfinished, or stop.

Trigger to Screen 4: the member reviews the final proposed private information and explicitly selects `Save privately`.

### 4. Saved Privately

The completion state must say:

`Saved privately. Nothing was added to your résumé, Feed, or public profile.`

The saved item shows classification, source, and AI-use permission. The member may edit it, change details, or view it in My Information.

Only after the private save is complete may Workshop offer one optional destination-specific draft. In the current example, that is a résumé bullet.

Creating a destination draft does not apply or publish it. Final approval remains in the existing destination.

### 5. My Information

This is the second mode rather than the next mandatory linear step.

The member can inspect exactly what has been confirmed, what remains suggested or unfinished, where an item is currently used, and whether AI may use it for private suggestions.

Editing or deleting private information must not silently rewrite an existing résumé, Feed item, or public-profile expression. Affected uses should be identified for separate review.

## AI role

AI may:

- retrieve relevant confirmed information;
- ask a small number of questions that materially improve the result;
- suggest wording, classifications, missing details, or connections;
- transform confirmed information into a separate destination-specific draft.

AI may not:

- silently confirm or save information;
- publish, apply, delete, or change downstream uses;
- collapse source words and AI interpretation into one truth;
- infer sensitive identity or personal facts without member initiation;
- score the person or frame them as deficient;
- repeatedly prompt after dismissal;
- make the core page unusable when AI is unavailable.

## Privacy and control

- Private by default.
- Identity and ownership must be server-derived in any future implementation.
- Authorization must occur before protected information is returned.
- Preserve original wording and provenance.
- Suggestions remain labeled and unconfirmed until accepted.
- Nothing publishes implicitly.
- The member may pause, save unfinished, stop, edit directly, archive, delete, or change AI-use permission.
- `Everything PeerSlate knows` is not the product promise. The bounded promise is information PeerSlate may use to understand and help represent the member.

## Outward destinations

Only these are in scope for this direction:

- résumé;
- Feed;
- public profile.

Workshop may prepare a draft, but it does not become the final publishing or destination-editing surface.

## Naming and language

- Product surface: **Workshop**.
- Modes: **Work on Something** and **My Information**.
- Optional suggestion: **Spark**.
- Spark is not a bot name.
- Classification: **Work**, **Personal**, **Both**, or left unclassified when needed.
- Avoid `weak`, `lacking`, `wrong`, or deficit-oriented language.

## Visual direction

- Professional, calm, contemporary, and trustworthy.
- AI-centric without becoming a chat transcript.
- Three-part studio rhythm: compact starting rail, dominant central workstage, restrained contextual rail.
- Serif/sans hierarchy and abstract pale gray-blue environment are the current candidate direction.
- Avoid navy, glassmorphism, neon, card-wall dashboards, gamification, and decorative excess.
- Final palette and background intensity remain deferred.
- Generated global-navigation content is placeholder and is not a product decision.

## Explicitly deferred or rejected

- Journal as a near-term dependency;
- whiteboard and Goal Board as the foundation of Workshop;
- new public Workshop pages;
- new destination pages;
- Story, Projects, interview answers, or other speculative destinations in this first direction;
- a separate drafts page, AI room, library destination, or publication-management area;
- résumé templates or full-document completion as the success unit;
- scoring, streaks, completeness meters, pressure, or identity homework.

