# Usar Node para construir
FROM node:20 as build

# Definir directorio de trabajo
WORKDIR /app

# Copiar solo package.json y package-lock.json primero
COPY package*.json ./

# Instalar dependencias limpio dentro del contenedor
RUN npm install

# Copiar el resto de la app (sin node_modules)
COPY . .

# Construir la aplicación
RUN npm run build

# Imagen final Nginx
FROM nginx:alpine

# Copiar el build
COPY --from=build /app/dist /usr/share/nginx/html

# Exponer el puerto
EXPOSE 80

# Arrancar Nginx
CMD ["nginx", "-g", "daemon off;"]
