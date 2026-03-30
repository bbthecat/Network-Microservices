FROM node:20-alpine

# Security: run as non-root
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Install dependencies first (layer caching)
COPY package*.json ./
RUN npm ci --only=production

# Copy app source
COPY --chown=appuser:appgroup . .

# Switch to non-root user
USER appuser

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
  CMD wget -qO- http://localhost:3000/health || exit 1

CMD ["node", "server.js"]
