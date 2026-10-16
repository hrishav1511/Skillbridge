# Multi-stage Dockerfile for Angular production build
# Builder: uses Node to install deps and build the app
FROM node:18-bullseye-slim AS builder
WORKDIR /app

# Install only what we need for installing/building packages, then clean up
COPY package.json package-lock.json* ./
RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates git python3 build-essential \
  && npm ci --silent \
  && apt-get purge -y --auto-remove git build-essential \
  && rm -rf /var/lib/apt/lists/* /root/.npm

# Copy source and build
COPY . .
RUN npm run build

# Production image: lightweight nginx serving the built SPA
FROM nginx:stable-alpine AS production

# Replace default nginx config with one that supports SPA client-side routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built output from builder (project name from package.json)
COPY --from=builder /app/dist/skillbridge-admin/ /usr/share/nginx/html/

EXPOSE 80
STOPSIGNAL SIGTERM
CMD ["nginx", "-g", "daemon off;"]
