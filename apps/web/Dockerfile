# syntax=docker.io/docker/dockerfile:1

FROM node:22-alpine AS base
RUN apk add --no-cache libc6-compat
RUN corepack enable && corepack prepare pnpm@latest --activate

# Dependencies
FROM base AS deps
WORKDIR /app

# Copy workspace config files
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/untitledui/package.json ./packages/untitledui/

RUN pnpm install --frozen-lockfile

# Build
FROM base AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules
COPY --from=deps /app/packages/untitledui/node_modules ./packages/untitledui/node_modules

COPY pnpm-workspace.yaml package.json ./
COPY apps/web ./apps/web
COPY packages/untitledui ./packages/untitledui

WORKDIR /app/apps/web

# Build with API_URL for rewrites
ARG API_URL=http://api:8000
ENV API_URL=${API_URL}
RUN pnpm build

# Production - use next start instead of standalone
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy the entire built app (not standalone)
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules
COPY --from=deps /app/packages/untitledui/node_modules ./packages/untitledui/node_modules
COPY --from=builder /app/apps/web/.next ./apps/web/.next
COPY --from=builder /app/apps/web/public ./apps/web/public
COPY --from=builder /app/apps/web/package.json ./apps/web/
COPY --from=builder /app/apps/web/next.config.ts ./apps/web/
COPY pnpm-workspace.yaml package.json ./
COPY packages/untitledui/package.json ./packages/untitledui/

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

WORKDIR /app/apps/web
CMD ["pnpm", "start"]
