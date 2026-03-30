FROM nginx:1.25-alpine

# Install wget for healthcheck
RUN apk add --no-cache wget

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom configs (mounted via volume in compose)
# These are mounted at runtime — Dockerfile just sets up the base image

EXPOSE 80 8000

CMD ["nginx", "-g", "daemon off;"]
