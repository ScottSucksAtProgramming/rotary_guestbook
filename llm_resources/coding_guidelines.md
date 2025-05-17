## Coding Guidelines & Best Practices: Rotary Guestbook

This document outlines the core principles and practices we will adhere to while developing and refactoring the Rotary Guestbook project. The goal is to produce clean, maintainable, robust, and extensible code.

### 1. General Clean Code Principles

*   **Readability is Key:**
    *   Write code that is easy for other developers (and your future self) to understand.
    *   Prefer clarity over overly clever or concise solutions if they sacrifice readability.
    *   Use consistent formatting (delegated to **Black**).
*   **Simplicity (KISS - Keep It Simple, Stupid):**
    *   Strive for the simplest solution that works. Avoid unnecessary complexity.
    *   Break down complex problems into smaller, manageable functions and classes.
*   **Meaningful Naming:**
    *   Use clear, descriptive names for variables, functions, classes, and modules.
    *   Names should reveal intent. Avoid abbreviations or single-letter names unless their scope is very small and context is obvious (e.g., loop counters `i`, `j`).
*   **Comments:**
    *   Comment *why* something is done, not *what* is being done (the code should explain the "what").
    *   Explain complex logic, assumptions, or workarounds.
    *   Update comments when code changes.
    *   **Docstrings are mandatory** for all public modules, classes, and functions (Google style, as per `context.md`).
*   **Don't Repeat Yourself (DRY):**
    *   Avoid duplicating code. Encapsulate common logic in functions or classes.
    *   Duplication is a common source of bugs when changes are needed.
*   **You Ain't Gonna Need It (YAGNI):**
    *   Implement only the functionality that is currently required.
    *   Avoid adding features or complexity "just in case" they might be needed later.

### 2. Object-Oriented Design (OOD) Principles

*   **Encapsulation:**
    *   Bundle data (attributes) and the methods that operate on that data within a class.
    *   Hide the internal state and complexity of an object; expose a clear public interface.
    *   Use private attributes (e.g., `_internal_var`) where appropriate, but Python relies on convention rather than strict enforcement.
*   **Abstraction:**
    *   Expose only essential information to the outside world, hiding unnecessary details.
    *   Focus on *what* an object does, not *how* it does it.
    *   Abstract Base Classes (ABCs) from Python's `abc` module are key tools for defining clear interfaces.
*   **Inheritance (Use Judiciously):**
    *   Allows new classes to receive (inherit) the properties and methods of existing classes (base/parent classes).
    *   Use for "is-a" relationships.
    *   **Prefer Composition over Inheritance** where possible to achieve greater flexibility and avoid tight coupling and deep inheritance hierarchies.
*   **Polymorphism:**
    *   "Many forms." Allows objects of different classes to respond to the same message (method call) in different ways.
    *   Often achieved through interfaces (ABCs) and method overriding.

### 3. SOLID Principles

*   **S - Single Responsibility Principle (SRP):**
    *   A class or module should have only one reason to change, meaning it should have only one job or responsibility.
    *   Leads to smaller, more focused, and more maintainable components.
*   **O - Open/Closed Principle (OCP):**
    *   Software entities (classes, modules, functions) should be open for extension but closed for modification.
    *   Achieve this through abstraction (interfaces/ABCs) and dependency injection, allowing new functionality to be added by creating new implementations of an interface rather than changing existing, stable code.
*   **L - Liskov Substitution Principle (LSP):**
    *   Subtypes must be substitutable for their base types without altering the correctness of the program.
    *   If class `S` is a subtype of class `T`, then objects of type `T` may be replaced with objects of type `S` without breaking the program.
    *   Pay attention to method signatures, return types, exceptions, and preconditions/postconditions in inherited methods.
*   **I - Interface Segregation Principle (ISP):**
    *   Clients should not be forced to depend on interfaces they do not use.
    *   Prefer many small, cohesive interfaces over large, monolithic ones.
    *   If a class implements an interface, it should use all of its methods.
*   **D - Dependency Inversion Principle (DIP):**
    *   High-level modules should not depend on low-level modules. Both should depend on abstractions (e.g., interfaces).
    *   Abstractions should not depend on details. Details should depend on abstractions.
    *   Use **Dependency Injection** to provide concrete implementations of dependencies to classes.

### 4. Other Important Practices

*   **Law of Demeter (Principle of Least Knowledge):**
    *   An object should only talk to its immediate "friends" (its own methods, parameters passed to its methods, objects it creates, direct component objects).
    *   Avoid long chains of calls like `object.get_part().get_another_part().do_something()`.
    *   Helps reduce coupling between classes.
*   **Composition over Inheritance:**
    *   Favor creating complex objects by composing simpler ones (has-a relationship) rather than inheriting from a base class (is-a relationship).
    *   Provides more flexibility, reduces coupling, and makes code easier to test and maintain.
*   **Test-Driven Development (TDD) / Writing Testable Code:**
    *   Write tests *before* or *alongside* your implementation code.
    *   Focus on small units of functionality.
    *   Code designed with testability in mind is often more modular, decoupled, and adheres to SRP and DIP.
    *   Ensure high test coverage (`pytest --cov`). Unit tests are crucial.
*   **Error Handling:**
    *   Use custom, specific exceptions (`src/rotary_guestbook/errors.py`).
    *   Catch exceptions at appropriate boundaries.
    *   Log errors effectively (`src/rotary_guestbook/logger.py`).
    *   Provide user-friendly error messages when applicable (e.g., in Web UI).
    *   Avoid catching generic `Exception` unless you specifically intend to and handle it properly (e.g., at the very top level of an application loop to log and prevent a crash).

### 5. Project-Specific Technical Stack & Reminders (from `context.md`)

*   **Python Version:** 3.10+ (target 3.12 for development).
*   **Type Hinting:** Use Python type hints for all function signatures and variables where beneficial. Enforced by `mypy --strict`.
*   **Docstrings:** Google style, 100% coverage enforced by `interrogate`.
*   **Formatting:** **Black** (enforced by pre-commit).
*   **Import Sorting:** **isort** (enforced by pre-commit).
*   **Linting:** **Flake8** (max line length 88, enforced by pre-commit).
*   **Modularity:** Strive for clear module separation as outlined in the project structure.
*   **Configuration:** Use `ConfigManager` for accessing application settings.

# Coding Guidelines (Update)

- All configuration code must use Pydantic v2 models, with `@field_validator` for validation and `model_dump()` for serialization.
- Any changes to configuration structure must be reflected in `config.yaml.example` and covered by unit tests to maintain 100% coverage.
- No linter or deprecation warnings are allowed in configuration code.
