# Dockerfile para Tailscale
FROM tailscale/tailscale:latest

# Configuración básica
RUN apt-get update && apt-get install -y net-tools
