FROM node:20.13-slim AS builder

WORKDIR /code

COPY ./package.json ./package-lock.json ./vite.config.mjs ./index.html ./
COPY ./src ./src
COPY ./public ./public

RUN npm install && npm run build

FROM nginx:1.19
COPY --from=builder /code/dist /usr/share/nginx/html