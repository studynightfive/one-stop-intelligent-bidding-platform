FROM node:24.16.0-alpine AS build

ARG VITE_API_BASE_URL=http://127.0.0.1:8210/api/v1
ARG VITE_USE_MOCKS=false

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_USE_MOCKS=${VITE_USE_MOCKS}

WORKDIR /workspace/demo
COPY demo/package.json demo/package-lock.json ./
RUN npm ci --ignore-scripts
COPY demo/ ./
COPY contracts/ /workspace/contracts/
RUN npm run contract:generate && npm run build

FROM nginx:1.27.1-alpine AS runtime
COPY infra/nginx/web.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/demo/dist /usr/share/nginx/html
EXPOSE 3210
