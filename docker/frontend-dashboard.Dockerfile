FROM node:20-alpine

WORKDIR /app

COPY frontend-dashboard/package.json frontend-dashboard/package-lock.json* ./

RUN npm install

COPY frontend-dashboard .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

