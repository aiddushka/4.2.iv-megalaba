FROM node:20-alpine

WORKDIR /app

COPY frontend-device-config/package.json frontend-device-config/package-lock.json* ./

RUN npm install --production=false

COPY frontend-device-config .

# Собираем прод-сборку и запускаем Vite preview-сервер на отдельном порту
RUN npm run build

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5174"]

