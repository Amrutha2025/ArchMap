# Multi-stage Dockerfile for React/Vite frontend (development optimized)

# ---- Build (Vite) ----
FROM node:18-bullseye-slim AS build
WORKDIR /app

# Install deps
COPY frontend/package*.json ./
RUN npm install --include=dev

# Copy source and build
COPY frontend/ ./
RUN npm run build

# ---- Runtime (static preview) ----
FROM node:18-bullseye-slim AS runtime
WORKDIR /app

# Install a lightweight static server
RUN npm install -g serve

# Copy built assets only
COPY --from=build /app/dist ./dist

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD wget -qO- http://localhost:3000 >/dev/null 2>&1 || exit 1

CMD ["serve", "-s", "dist", "-l", "3000"]
