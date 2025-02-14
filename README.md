# Precision Farming

## Purpose
Purpose of this project is to build a precision engine that can help farmers automate their farming operations. And do so in a very optimal way. 

<img width="612" alt="image" src="https://github.com/user-attachments/assets/30268dfd-f121-43b4-b319-2b885098d775">

The vision for the end result is
- recommend the best time to plant the crops taking into account the climate requirements and the forecast of the best time to sell the crop
- Once planted, automate the aggregation of data
  - soil information from gauges in the farm land
  - weather information from weather APIs
  - insect and disease images from drones
- With real time data, make decisions on actions to take, define specific actions for the centralling controlled farm equipment

Current state of the project has built a RAG based core Precision Farming engine that 
- takes user inputs (did not have access to soil meters and drones),
- analyzes the specific of the crop and decides on the action plan
- gives the action plan and rationale as a narrative back to the farmer (did not have access to farm equipment)

<img width="612" alt="image" src="https://github.com/user-attachments/assets/bcb426a8-84d4-4d69-9d28-867b07f63714">

## Table of Contents
- [Purpose](#Purpose)
- [Overview](#Overview)
- [Architetcure](#Architecture)
- [Technical Details](#Implementation)
- [Result](#Result)
- [License](#License)

## Overview of the core engine

The core engine is developed using OpenAI and Azure AI Search. The engine takes a methodical approach to understanding the current state, analyzing it, and recommending a course of action. 

- Collect user input of location, crop, current soil moisture, insect image, leaf image
- gets 7 day weather forecast and recommends irrigation plan
- Predicts the insect in given image. Suggests actions to take based on information in crop guides available in vector stores
- Predicts the disease based on crop leaf image. Suggests action to take based on information in crop guides available in vector stores
- Get optimal PH and moisture levels. Suggests actions to take based on information in crop guides available in vector stores
- Searches the web incase relevent infromation is not available in the vector store
- Finally, puts its all toegther into a actionable plan for the farmer

## Architecture

The core of the application is built on Azure OpenAI, Azure AI Search for RAG. Orchestration/workflow is through LanGraph and LangChain with deployment on Azure Application Services. 

<img width="458" alt="image" src="https://github.com/user-attachments/assets/207e88c5-b4fb-4e31-ac46-05e8c2f73525">

1. **Frontend/UI (Streamlit)**:
   - **Streamlit Application**: The frontend that farmers interact with to input data such as location, soil moisture, insect images, and crop type.

2. **Backend Services**:
   - **Core Engine**: The central component that handles decision-making using LangChain, LangGraph, and OpenAI to provide insights and recommendations.
   - **Azure AI Search (Vector Database)**: Stores crop guides (for soybeans, corn, cotton) and enables retrieval for decision-making. This database can be populated by running the `CropvectorStoreAzureAISearch.py` script.
   - **Weather API Integration**: Fetches real-time weather data to guide irrigation and planting recommendations.
   - **Image Classification (TensorFlow)**: Identifies pests and leaf diseases using CNN.

3. **Data Flow**:
   - **User Input**: Farmers provide input such as location, crop type, soil moisture, insect images, and leaf images.
   - **Workflow Engine (LangChain, LangGraph)**: Based on inputs, the engine retrieves relevant data from the vector database and integrates weather API information to recommend actions.
   - **Action Plan**: Outputs the recommended action plan for the farmer, such as when to water, how to treat pests, etc.

4. **Containerization (Docker)**:
   - The application is containerized using Docker and pushed to **Azure Container Registry (ACR)**.

5. **Deployment (Azure Web App)**:
   - The Docker container is deployed to an **Azure Web App**, allowing farmers to access the application via a web interface.
   - The application scales using Azure’s platform-as-a-service (PaaS) capabilities.

## Implementation
The anchor for the graph is a function calling agentic workflow that uses Open AI and LangGraph. The graph has at its disposal few tools that it can decide to call based on the need. And once it has all the informationm, it puts together a structured markdown response to be given back to the user.


<img width="612" alt="image" src="https://github.com/user-attachments/assets/36a6b7e8-48be-4b84-b568-e2e54f3bc644">


*** Key Decision: *** The controlling is an agentic tool based workflow with just the nodes to call tools and LLM. We decided to go with this approach instead of a well defined graph and nodes to ensure that the core graph can be chatty and refine the response as needed to meet the expectatios of the prompt. In contrary, the retrieval graph is well defined with specific nodes and conditional edges that takes a task from START to END. Retrieval graph was define in that way since we knew exactly how to get a well grounded intermediate response.  

### Tools

<p> decrease_ph and increase_ph - These are simple python functions annotated with @tool and does a predefined mathematical calculation on the about of chemicals to use to alter the PH to desired levels. <p>

get_weather_data - This uses the "weatherapi" API to get 7 day forecast for the location provided

calculate_water_needed - Simple python function that tells us how much water we need to get the soil moisture level to where we need it to be.

get_crop_info - generic funtion that uses the retrieval graph to answer questions that are not addressed by earlier defiend tools. Relies first on the crop production guides and then on web search

tackle_insect, tackle_disease - uses the retrieval graph to get needed information from the crop production guides that are chunked and stored in the vector database. Falls back on websearch if needed.

### Nodes in retreival graph

Below parts together for a Corrective RAG system gets the best possible retrieval using multi-query, query rewriting, active retrieval.

Retrieve - Uses multi query translation to break down larger and complex queries into simple questions to do a vector search on.  Use a relevence search to get the most appropriate content for you.


Context relevance - Uses trulens to confirm that retrieved context is relevent to the question to answer. Since we are using trulens.apps.langchain.**WithFeedbackFilterDocuments**, we only need to check if there is any document available in the "documents" state

Web Search - Performs a websearch using Tivaly to get information in case reteival does not give us the needed information. Part of the **CRAG system**.

Generate Response - Simple LLM call with context to generate the answer. 

Response Grounded - Checks if the response is grounded using upstage. 

Transform Query - Rewrite the whole question if needed.

### Image Classification - Insect and Leaf (CNN using Tensorflow)

Fine-tuning of the ImageNet with softmax in last layer for multiclass classification. 

## Getting Started

***To run this locally***, you can do the following on command prompt
```commandline
git clone https://github.com/dheerajrhegde/PrecisionFarming
cd PrecisionFarming
```
Go into the code root folder, create and activate a virtual environmetn
```commandline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Setup API keys that the code uses to access OpenAI and other services. You can get your API keys from the below websites

https://platform.openai.com/

https://tavily.com

https://console.upstage.ai/home

https://www.weatherapi.com

```commandline
export OPENAI_API_KEY="your API key"
export TAVILY_API_KEY="your API key"
export UPSTAGE_API_KEY="your API key"
export WEATHER_API_KEY="your API key"
streamlit run StreamLitApp.py
```

***Deploying on Azure WebApp***

Prerequisites - Docker installed on your laptop (Linux) or Azure VM. Can be installed using this convenience script.
```commandline
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

clone the repository. 
```commandlline
git clone https://github.com/dheerajrhegde/PrecisionFarming/tree/main
```

Build the docker image (using provided Dockerfile). Very that image is created
```commandline
sudo docker build -t precision-farming-app .
sudo docker images
```

Run the docker image as a container and ensure it is running.
```commandline
sudo docker run -p 8501:8501 precision-farming-app
sudo docker ps
```

Verify application us running and working as expeceted using https://localhost:8501/. If you are using Azure VM, make sure you have an NSG for your resource group and allow ingress and egress. 

Create an Azure Container Registry at https://portal.azure.com. Collect the access credentials from "access keys"
Install Azure CLI and authenticate your self using 
```commandline
az login
```

Authenticate and access container registry. And push the image to the ACR
```commandline
az acr login --name azureraghackathon
sudo docker tag precision-farming-app:latest raghackathon.azurecr.io/precision-farming-app:latest
sudo docker push raghackathon.azurecr.io/precision-farming-app:latest
```

Create a webap on https://portal.azure.com/. Make sure you select
- Instance Details Publish as "Container" in Basics tab
- In container tab, select image soruce as "Azure Container registry"

Select your container image and deploy after entering other required fields. Once deployed, use the Default Domain from the App Service and access the application.




## Result
<img width="1117" alt="image" src="https://github.com/user-attachments/assets/fb76a47c-2f11-4896-9921-7174af7a58bd">

## License
MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


