FROM nginx:alpine

# Copy the HTML file to nginx default directory
COPY index.html /usr/share/nginx/html/

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
