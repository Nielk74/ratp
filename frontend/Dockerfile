FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ENV NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
