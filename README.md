# Kwik

<div align="center">
<img src="docs/handbook/docs/img/logo.png" alt="Kwik Logo" width="400">
</div>

> **⚠️ Pre-Release Software Warning**
> 
> Kwik is currently in active development and has not yet reached version 1.0. The internal APIs, data structures, and framework interfaces are subject to change without notice. While we strive to maintain backward compatibility where possible, breaking changes may occur as we refine the framework for the v1.0 release.
> 
> **Not recommended for production use until v1.0 is released.**

---

**Documentation**: https://davide.mezzogori.com/kwik/

**Repository**: https://github.com/dmezzogori/kwik

[![codecov](https://codecov.io/github/dmezzogori/kwik/branch/main/graph/badge.svg?token=7WBOPGCSWS)](https://codecov.io/github/dmezzogori/kwik)
---

Kwik is a web framework for building modern, batteries-included, REST APIs backends with Python 3.12+.
Kwik is based on FastAPI, builds upon it and delivers an opinionated, concise, and business-oriented API.


## Acknowledgments

Python 3.12+

Kwik stands on the shoulder of a couple of giants:

* [FastAPI](https://fastapi.tiangolo.com/): for the underlying REST API server.
* [Pydantic](https://docs.pydantic.dev/1.10/): for the data validation and serialization.
* [SQLAlchemy](https://www.sqlalchemy.org/): for the ORM part.

## Installation

```console
$ pip install kwik
```

or

```console
$ uv add kwik
```

It will install Kwik and all its dependencies.

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/dmezzogori/kwik.git
cd kwik

# Install dependencies using uv
uv sync

# Start development server with hot reload
kwik
```

### Testing

```bash
# Run all tests with coverage (testcontainers automatically manages PostgreSQL)
pytest --cov=src/kwik --cov-report=term-missing

# Run tests in parallel (faster)
pytest -n auto

# Run specific test file
pytest tests/crud/test_crud_users.py

# Run only unit tests (skip integration tests)
pytest -m "not integration"
```

**Note**: Tests use testcontainers to automatically manage the PostgreSQL database. No manual database setup required (just docker).

### Code Quality

```bash
# Run linter and formatter
ruff check
ruff format
```

### Documentation

```bash
# Start documentation website locally
cd docs
docker compose up

# Access at http://localhost:8000
```

### Contributing

1. Create a feature branch (`git checkout -b feature/your-feature-name`)
2. Make your changes following the existing code style
3. Add tests for new functionality
4. Run tests and ensure they pass
5. Run linting and fix any issues
6. Commit your changes (`git commit -am '<Your commit message>'`)
7. Push to the branch (`git push origin feature/your-feature-name`)
8. Create a Pull Request

## License

This project is licensed under the terms of the MIT license.
