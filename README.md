# fast-agents

## 项目架构(未完善)

```
.
├── app
│   ├── api
│   │   ├── __init__.py
│   │   └── v1
│   │       ├── __init__.py
│   │       └── endpoints.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── utils.py
│   ├── models
│   │   ├── __init__.py
│   │   └── user.py
│   ├── services
│   │   ├── __init__.py
│   │   └── user_service.py
│   ├── __init__.py
│   ├── main.py
│   └── config.py
└── tests
    ├── __init__.py
    ├── conftest.py
    └── end_to_end
        ├── __init__.py
        └── test_endpoints.py

```