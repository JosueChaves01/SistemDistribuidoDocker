# Usar una imagen de Node para construir la app
FROM node:20 as build

# Definir el directorio de trabajo
WORKDIR /app

# Copiar el package.json y package-lock.json
COPY package*.json ./

# Instalar las dependencias
RUN npm install

# Copiar el resto del código de la aplicación
COPY . .

# Construir la aplicación para producción
RUN npm run build

# Usar una imagen de Nginx para servir la app
FROM nginx:alpine

# Copiar el build generado al directorio de Nginx
COPY --from=build /app/build /usr/share/nginx/html

# Copiar un archivo de configuración de Nginx (opcional)
# COPY nginx.conf /etc/nginx/nginx.conf

# Exponer el puerto 80
EXPOSE 80

# Arrancar Nginx
CMD ["nginx", "-g", "daemon off;"]
