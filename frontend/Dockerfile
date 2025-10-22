FROM nginx:alpine

# Copy all HTML files to nginx default directory
COPY *.html /usr/share/nginx/html/

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
