FROM nginx:alpine

# Copiar archivos estáticos iniciales
# En fases posteriores esto se reemplazará por el build de React/Vite
COPY . /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
