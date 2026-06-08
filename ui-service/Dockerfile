FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 8002

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "8002"]
