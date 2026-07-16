# Required diagrams (current state + v1.2 target)

## 1. Viewer modes and routes (current — pre-auth)

```mermaid
flowchart LR
    V[Any visitor - no auth yet] --> M["/ homepage · /peerslate About · /experience"]
    V --> P["Pete public profile\n/petec/my-story · skills(Evidence) · slate-board · resume · projects"]
    V --> C["Community /the-slate\ncorkboard + rails (fixtures)"]
    V --> F["/feed-living-stream\nlabeled design preview"]
    V --> I["/interview-studio\nreal AI endpoints, no persistence"]
    V --> A["Ask Pete AI (/api/chat)\npublic-approved sources only"]
    subgraph next phase
        L[Sign in - Azure Easy Auth scaffolding in identity.py]
        L --> O[Owner views - Pete/Danielle]
    end
```

## 2. Capture → Journal → publication → Feed (v1.2 target; Journal HELD)

```mermaid
flowchart LR
    Cap[Universal Capture\ntext/voice/photo/video/doc] --> D[Private draft]
    D -->|member approves| J[(Journal - canonical record)]
    J -->|publish, audience chosen| FP[Feed projection - reference, not copy]
    J --> PT[Project/Goal timeline - same record]
    J --> PJ[Public Journal view - audience filtered]
    style J stroke:#5A2D82,stroke-width:3px
```
Current reality: no Journal store; corkboard + preview posts are fixtures.

## 3. Document upload → AI retrieval (v1.2 target; auth-gated)

```mermaid
flowchart LR
    U[Upload JD - PDF/DOCX/TXT] --> S[Session-private document\nvalidated + scanned]
    S --> X[Extraction: basic/preferred quals + excerpts]
    X --> Q[Qualification matching vs confirmed history]
    Q --> R[Coverage scores + per-qual verdicts]
    S -.never.-> Pub[Public listing/index/Feed]
```

## 4. Interview flow (v1.2 target; public-safe slice now)

```mermaid
flowchart LR
    Q2[Question] --> A2[Member answer - voice or text]
    A2 --> FB[Feedback: What worked · Improve next ·\nFollow-up · Relevant history you may have missed]
    FB --> F1[Answer follow-up]
    FB --> F2[Improve this answer - separate draft]
    FB --> F3[Save as interview story - PRIVATE DRAFT - auth phase]
    A2 --> Mode{Interview AI mode}
    Mode --> BP[Best-practice example - generic, labeled]
    Mode --> MH[Use my history - permitted history shown]
    Mode --> CP[Compare - stacked, structural lessons]
```

## 5. Resume Creator / Constellation relationships (v1.2 target)

```mermaid
flowchart TD
    Role[Role/employer anchor] --- Proj[Project - may span roles]
    Proj --- Ach[Achievement]
    Role --- Promo[Promotion - explicit member-confirmed event]
    Role & Proj & Ach & Promo --> CC[Career Constellation - audience filtered]
    Role & Proj & Ach & Promo --> RC[Resume Creator version\nwording variants, source links]
    RC --> PDF[PDF/DOCX export - snapshot, not source of truth]
```
