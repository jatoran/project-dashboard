FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
RUN uv sync --frozen --no-install-project

# Copy the application code
# We copy to /app/backend so that 'backend' is treated as a package
COPY . /app/backend

# Set PYTHONPATH so python can find the 'backend' package
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# Expose the port defined in the code/requirements
EXPOSE 37453

# Run the application
# We use 'uv run' to ensure we use the environment's dependencies, though adding .venv/bin to PATH also works.
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "37453"]
