FROM node:20-alpine

WORKDIR /app

COPY apps/frontend/package.json ./apps/frontend/package.json
COPY packages/api-client ./packages/api-client

WORKDIR /app/apps/frontend
RUN npm install

COPY apps/frontend .

EXPOSE 5173

CMD ["npm", "run", "dev"]
