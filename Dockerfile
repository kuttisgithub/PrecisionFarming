# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TAVILY_API_KEY="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"
ENV AZURE_SEARCH_ENDPOINT="https://search-mpho4rxdt6mya.search.windows.net"
ENV AZURE_SEARCH_ADMIN_KEY="AO5U5uJDGbCJRbkCQ2cprlVjnvlQWRz3N7DJnzbe3rAzSeAX65v5"
ENV TAVILY_API_KEY="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"

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that Streamlit runs on
#EXPOSE 8501

# Run the vector store creation script before the Streamlit app
# This runs CropvectorStore.py before starting the Streamlit app
#RUN python CropVectorStoreAzureAISearch.py

# Command to run the Streamlit application
#CMD ["streamlit", "run", "StreamLitApp.py"]
EXPOSE 80
CMD ["python", "app.py"]
