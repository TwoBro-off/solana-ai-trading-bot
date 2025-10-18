
# Use multi-arch Python base image for ARM64/x86_64 compatibility
FROM --platform=$BUILDPLATFORM python:3.10-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app

# Create app directory
WORKDIR $APP_HOME


# Install system dependencies (universal for ARM/x86_64)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        pkg-config \
        libssl-dev \
        libffi-dev \
        libsodium-dev \
        sqlite3 \
        libsqlite3-dev \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ $APP_HOME/backend/


# Install Node.js 20.x and Yarn (universal for ARM/x86_64)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g yarn \
    && node --version && yarn --version

COPY frontend/package.json $APP_HOME/frontend/
COPY frontend/yarn.lock $APP_HOME/frontend/
COPY frontend/public $APP_HOME/frontend/public
COPY frontend/src $APP_HOME/frontend/src

WORKDIR $APP_HOME/frontend
RUN yarn install --no-lockfile
RUN yarn build

RUN mkdir -p $APP_HOME/backend/static
RUN cp -r $APP_HOME/frontend/build/* $APP_HOME/backend/static/

WORKDIR $APP_HOME
RUN rm -rf $APP_HOME/frontend

# Clean up Node/Yarn cache for smaller image
RUN yarn cache clean && npm cache clean --force


EXPOSE 8000
CMD ["python", "backend/main.py"]