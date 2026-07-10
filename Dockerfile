FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        unzip \
        git \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Deno — persist to /usr/local/bin so it's always on PATH
RUN curl -fsSL https://deno.land/install.sh | sh \
    && cp /root/.deno/bin/deno /usr/local/bin/deno

# Verify deno is accessible
RUN deno --version

# Install uv (fast Python package manager)
RUN curl -Ls https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy dependency spec and install Python deps first (layer caching)
COPY pyproject.toml ./
RUN uv sync --no-dev

# Copy the rest of the project
COPY . .

# Create necessary runtime directories
RUN mkdir -p downloads cache ishu/cookies

CMD ["bash", "start"]
