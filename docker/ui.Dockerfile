# syntax=docker/dockerfile:1.7

FROM node:20-bookworm-slim AS builder

ENV NODE_OPTIONS=--max-old-space-size=4096 \
    NEXT_TELEMETRY_DISABLED=1

WORKDIR /app/ui

RUN corepack enable

COPY ui/package.json ui/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY ui ./

RUN pnpm exec next build --webpack && pnpm prune --prod

FROM node:20-bookworm-slim AS runtime

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /app/ui

COPY --from=builder /app/ui/package.json ./package.json
COPY --from=builder /app/ui/public ./public
COPY --from=builder /app/ui/.next ./.next
COPY --from=builder /app/ui/node_modules ./node_modules

EXPOSE 3000

CMD ["node_modules/.bin/next", "start", "--hostname", "0.0.0.0", "--port", "3000"]
