# Use the official Node.js image as the base image
FROM node:14

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY text-assistant/package*.json ./

# Install the app dependencies
RUN npm install

# Copy the rest of the application code to the working directory
COPY text-assistant/ .

# Build the application
RUN npm run build

# Expose the port the app runs on
EXPOSE 3000

# Define the command to run the app
CMD ["npm", "start"]
