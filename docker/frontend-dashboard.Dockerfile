FROM node:20-alpine

WORKDIR /app

COPY frontend-dashboard/package.json frontend-dashboard/package-lock.json* ./

RUN npm install --production=false

COPY frontend-dashboard .

# Собираем прод-сборку и запускаем Vite preview-сервер
RUN npm run build

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]

