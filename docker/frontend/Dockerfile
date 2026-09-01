# Multi-stage Next.js build. `dev` stage is used by docker-compose.yml for
# local development (hot reload against a bind-mounted source tree); `runner`
# is the production stage, selected by docker-compose.prod.yml via `target:`.
# Requires next.config.ts to set `output: "standalone"` (added in Phase 6)
# so the runner stage can run without a full node_modules tree.

FROM node:22-alpine AS base
WORKDIR /app

FROM base AS deps
COPY package.json package-lock.json* ./
RUN npm ci

FROM base AS dev
ENV NODE_ENV=development
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM base AS builder
ENV NODE_ENV=production
# Next.js inlines NEXT_PUBLIC_* into the static client bundle at build time —
# unlike the `dev` stage above (where the Next dev server reads them fresh
# from the container's runtime environment), setting these via env_file/
# environment: on the running container has no effect once this stage has
# already built. Must be passed as --build-arg (see docker-compose.prod.yml's
# `frontend.build.args`), not left as plain runtime env vars.
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_WS_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV NEXT_PUBLIC_WS_BASE_URL=${NEXT_PUBLIC_WS_BASE_URL}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM base AS runner
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
