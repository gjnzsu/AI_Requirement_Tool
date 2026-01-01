# Authentication Flow - Protected Endpoint Access (Simplified)

This diagram focuses on the protected endpoint access flow - the most common authentication flow that occurs on every API request after login.

```mermaid
sequenceDiagram
    participant User
    participant Frontend as Frontend
    participant FlaskApp as Flask App
    participant Middleware as Auth Middleware
    participant AuthService as AuthService
    participant UserService as UserService
    participant Database as Database

    User->>Frontend: Request protected resource
    Frontend->>FlaskApp: HTTP Request with Authorization Bearer token
    
    FlaskApp->>Middleware: token_required decorator
    
    Middleware->>AuthService: Extract and verify token
    AuthService->>AuthService: jwt.decode(token)
    
    alt Token Invalid or Expired
        AuthService-->>Middleware: Token invalid
        Middleware-->>FlaskApp: 401 Unauthorized
        FlaskApp-->>Frontend: 401 Error
        Frontend->>Frontend: Clear token and redirect to login
        Frontend-->>User: Session expired
    else Token Valid
        AuthService-->>Middleware: Payload with user_id and username
        Middleware->>UserService: get_user_by_id(user_id)
        UserService->>Database: SELECT user WHERE id
        Database-->>UserService: User record
        UserService-->>Middleware: User object
        
        alt User Not Found or Inactive
            Middleware-->>FlaskApp: 401 Unauthorized
            FlaskApp-->>Frontend: 401 Error
            Frontend-->>User: Access denied
        else User Active
            Middleware->>Middleware: Attach user to request
            Middleware-->>FlaskApp: Continue to handler
            FlaskApp->>FlaskApp: Process request
            FlaskApp-->>Frontend: 200 OK with response
            Frontend-->>User: Success
        end
    end
```

