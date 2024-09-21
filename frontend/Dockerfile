FROM node:20.13.1-slim

WORKDIR /code
COPY ./package.json ./package-lock.json ./

RUN npm install

COPY jsconfig.json ./
COPY index.html ./
COPY vite.config.mjs ./
COPY eslint.config.js ./

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
