# Course Registration Example

A REST API backend for managing student course enrollments.

## Specs

```
course-registration/
├── entities/
│   ├── student.spec      # Student records and eligibility
│   ├── course.spec       # Course offerings and capacity
│   └── enrollment.spec   # Student-course relationships
├── services/
│   └── enrollment-service.spec  # Enrollment business logic
└── api/
    └── enrollment-api.spec      # REST endpoints
```

## Dependency Graph

```
enrollment-api
    └── enrollment-service
            ├── student
            ├── course
            └── enrollment
                    ├── student
                    └── course
```

## Domain Overview

Students can enroll in courses if they are active and the course has available capacity. The system tracks enrollments and allows students to withdraw while preserving history.
