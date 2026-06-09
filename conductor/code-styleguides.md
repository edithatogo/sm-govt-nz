# Code Styleguides - NZ Government Bluesky Syndicator & Transparency Hub

## Python Style Guide
*   **Standards:** PEP 8 (Standard style guide for Python).
*   **Tooling:** **Ruff** for linting and formatting.
*   **Formatting Rules:**
    *   Line length: 88 characters (standard for Ruff/Black).
    *   Indentation: 4 spaces.
    *   Imports: Grouped and sorted (stdlib, third-party, local).
*   **Docstrings & Comments:**
    *   Use triple double quotes `"""` for module, class, and function docstrings.
    *   Write docstrings explaining parameters, returns, and exceptions where applicable.

## Frontend Style Guide (HTML, CSS, JS)

### 1. HTML5 (Semantic Structure)
*   Use standard semantic HTML5 tags (e.g., `<header>`, `<main>`, `<section>`, `<footer>`, `<article>`).
*   Ensure all images have `alt` tags for accessibility.
*   Validate HTML structures to ensure clean document models.

### 2. CSS3 (Modern Styling Tokens)
*   **Theme Management:** Define layout and branding parameters using CSS Custom Properties (variables) in the `:root` scope (e.g., `--color-primary`, `--font-main`).
*   **Layouts:** Use Flexbox and CSS Grid for responsive design. Avoid floats and inline styles.
*   **Naming:** Maintain descriptive, lowercase class names separated by hyphens (e.g., `.profile-card`, `.nav-link`).

### 3. JavaScript (ES6+ Standards)
*   **Syntax:** Use `const` and `let` for variable declarations. Avoid `var`.
*   **Structure:** Write standard ES6+ modules and arrow functions.
*   **API Calls:** Use `async/await` syntax for asynchronous requests and always include `try/catch` blocks for robust error handling.
