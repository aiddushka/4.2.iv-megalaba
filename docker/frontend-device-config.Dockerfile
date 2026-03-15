FROM node:20-alpine

WORKDIR /app

COPY frontend-device-config/package.json frontend-device-config/package-lock.json* ./

RUN npm install

COPY frontend-device-config .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

