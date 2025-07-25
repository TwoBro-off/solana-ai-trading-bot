# Use a lightweight ARM64 base image for Python
FROM arm64v8/python:3.9-slim-buster

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV APP_HOME /app

# Create app directory
WORKDIR $APP_HOME

# Install system dependencies
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
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ $APP_HOME/backend/

# Install Node.js for frontend build (using nvm for ARM64 compatibility)
# Note: This approach is more robust for ARM64 as official Node.js images might not always be up-to-date for all ARM variants.
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash
ENV NVM_DIR /root/.nvm
RUN bash -c "$NVM_DIR/nvm.sh && nvm install 16 && nvm use 16 && nvm alias default 16"
ENV NODE_PATH $NVM_DIR/versions/node/v16.20.2/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v16.20.2/bin:$PATH

# Install frontend dependencies and build
COPY frontend/package.json $APP_HOME/frontend/
COPY frontend/yarn.lock $APP_HOME/frontend/
WORKDIR $APP_HOME/frontend
RUN yarn install --frozen-lockfile
RUN yarn build

# Copy built frontend to a static serve directory in backend
RUN mkdir -p $APP_HOME/backend/static
RUN cp -r $APP_HOME/frontend/build/* $APP_HOME/backend/static/

# Clean up Node.js and frontend build artifacts to reduce image size
WORKDIR $APP_HOME
RUN rm -rf $APP_HOME/frontend
RUN rm -rf $NVM_DIR

# Expose port for the backend API
EXPOSE 8000

# Set entrypoint to run the backend application
CMD ["python", "backend/main.py"]