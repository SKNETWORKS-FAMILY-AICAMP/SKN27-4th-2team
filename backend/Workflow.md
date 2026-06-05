- Workflow
```mermaid
flowchart TD
    A["사용자 메시지"] --> B["User Analysis Agent"]
    B --> C{"Supervisor Router"}

    C -->|"케어 질문"| D["Care Consultation Agent"]
    C -->|"특정 견종 질문"| E["Breed Information Agent"]
    C -->|"견종 추천 요청"| F{"추천 정보 충분?"}
    C -->|"지원 범위 외"| G["지원 범위 안내"]

    F -->|"부족"| H["Clarification Agent"]
    F -->|"충분"| I["Breed Recommendation Agent"]

    D --> J["RAG Tool"]
    E --> K["Breed Repository Tool"]
    K --> J
    I --> L["Scoring Tool"]
    L --> J

    J --> M["Response Generator"]
    M --> N["Response Validator"]
    N --> O["최종 답변"]
```




- 권장 파일 구성
backend/
├── agents/
│   ├── state.py
│   ├── graph.py
│   ├── supervisor.py
│   ├── user_analysis_agent.py
│   ├── care_consultation_agent.py
│   ├── breed_information_agent.py
│   ├── breed_recommendation_agent.py
│   ├── clarification_agent.py
│   └── response_validation_agent.py
│
├── tools/
│   ├── breed_repository.py
│   ├── breed_scoring.py
│   ├── profile_manager.py
│   └── rag_client.py
│
└── schemas/
    ├── user_profile.py
    ├── recommendation.py
    └── retrieved_document.py