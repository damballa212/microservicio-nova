
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app

# Instalar dependencias necesarias para node-gyp o compilaciones nativas si fuera necesario
RUN apk add --no-cache libc6-compat

# Copiar archivos de definición de dependencias
COPY package.json package-lock.json* ./
RUN npm ci

# Copiar el resto del código
COPY . .

# Variables de entorno necesarias durante el build (si aplica)
# Nota: Las variables NEXT_PUBLIC_ se inyectan en el bundle JS. 
# Si quieres que sean dinámicas en runtime, usualmente se inyectan aquí o se usa un patrón de runtime config.
ARG NEXT_PUBLIC_API_URL=https://flowify-crm-nova-ai.lsoqoe.easypanel.host
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# Stage 2: Runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
# Deshabilitar telemetría de Next.js durante el runtime
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copiar los archivos necesarios desde el builder (usando standalone)
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
# Configurar la URL de host para que escuche en todas las interfaces
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
