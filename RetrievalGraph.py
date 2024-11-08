from typing import List
from typing_extensions import TypedDict
import pprint
import os
import time
import asyncio
from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain.schema import Document
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_upstage import UpstageGroundednessCheck
from langchain.chains.query_constructor.base import AttributeInfo
from langgraph.graph import END, START, StateGraph
from trulens.apps.langchain import WithFeedbackFilterDocuments
from trulens.core import Feedback
from trulens.providers.openai import AzureOpenAI
from langchain.load import dumps, loads

UPSTAGE_API_KEY = "up_VjWl59uApKL4H69akYmQJNRGEjR2H"
AZURE_DEPLOYMENT = "gpt-4o"
API_VERSION = "2024-05-01-preview"
AZURE_ENDPOINT = "https://agtech-llm-openai.openai.azure.com"
API_KEY = "5366f9c0121f4852afeb69388c2aff3a"

class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""
    binary_score: str = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )

class GraphState(TypedDict):
    """Represents the state of our graph."""
    crop: str
    question: str
    generation: str
    web_search: str
    documents: List[str]
    groundedness: str

class RetrievalGraph:
    def __init__(self):
        # Initialize Tavily
        self.web_search_tool = TavilySearchResults(k=3)
        self.llm = AzureChatOpenAI(
            azure_deployment=AZURE_DEPLOYMENT,
            api_version=API_VERSION,
            azure_endpoint=AZURE_ENDPOINT,
            api_key=API_KEY,
            temperature=0
        )

        # Initialize Azure Search with batched embeddings
        model = "text-embedding-ada-002"
        vector_store_address = os.getenv("AZURE_SEARCH_ENDPOINT")
        vector_store_password = os.getenv("AZURE_SEARCH_ADMIN_KEY")
        
        self.embeddings = AzureOpenAIEmbeddings(
            api_key=API_KEY,
            model=model,
            azure_endpoint=AZURE_ENDPOINT,
            chunk_size=16  # Process 16 embeddings at once
        )

        from langchain_community.vectorstores.azuresearch import AzureSearch
        index_name: str = "crop_guide"

        self.vectorstore = AzureSearch(
            azure_search_endpoint=vector_store_address,
            azure_search_key=vector_store_password,
            index_name=index_name,
            embedding_function=self.batch_embed_queries,
        )

        # RAG Chain setup
        prompt = hub.pull("rlm/rag-prompt")
        self.rag_chain = prompt | self.llm | StrOutputParser()

        # Question rewriting setup
        system = """You are a question re-writer that converts an input question to a better version that is optimized \n 
                   for web search. Look at the input and try to reason about the underlying semantic intent / meaning."""
        self.rewrite_prompt = ChatPromptTemplate.from_messages([
            ("system", system),
            ("human", "Here is the initial question: \n\n {question} \n Formulate an improved question."),
        ])
        self.question_rewriter = self.rewrite_prompt | self.llm | StrOutputParser()

        # Query generation setup
        self.query_template = """You are an AI language model assistant. Your task is to break down the larger question
            into smaller subquestions for vector store retrieval.
            Original question: {question}
            Crop: {crop}
            """
        self.query_prompt = ChatPromptTemplate.from_template(self.query_template)
        self.generate_queries = (
            self.query_prompt 
            | self.llm 
            | StrOutputParser() 
            | (lambda x: x.split("\n"))
        )

        # Initialize workflow graph
        workflow = StateGraph(GraphState)
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("generate", self.generate)
        workflow.add_node("transform_query", self.transform_query)
        workflow.add_node("web_search_node", self.web_search)

        # Build graph connections
        workflow.add_edge(START, "retrieve")
        workflow.add_conditional_edges(
            "retrieve",
            self.nothing_retrieved,
            {
                "web_search": "web_search_node",
                "generate": "generate",
            },
        )
        workflow.add_edge("web_search_node", "generate")
        workflow.add_conditional_edges(
            "generate",
            self.not_grounded,
            {
                "notGrounded": "transform_query",
                "notSure": "transform_query",
                "grounded": END
            }
        )
        workflow.add_edge("transform_query", "retrieve")

        self.app = workflow.compile()

    def batch_embed_queries(self, texts: List[str]) -> List[List[float]]:
        """Batch process embeddings with rate limiting"""
        if not isinstance(texts, list):
            texts = [texts]
            
        BATCH_SIZE = 16
        all_embeddings = []
        
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            
            if i > 0:
                time.sleep(1)  # Rate limiting delay between batches
                
            try:
                batch_embeddings = self.embeddings.embed_documents(batch)
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                print(f"Batch embedding error: {e}")
                # Fallback to individual processing
                for text in batch:
                    try:
                        embedding = self.embeddings.embed_query(text)
                        all_embeddings.append(embedding)
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"Individual embedding error: {e}")
                        all_embeddings.append([0.0] * 1536)
                        
        return all_embeddings[0] if len(texts) == 1 else all_embeddings

    async def async_retrieve_docs(self, questions: List[str]):
        """Asynchronously retrieve documents for multiple questions"""
        async def get_docs(question):
            return self.vectorstore.similarity_search(question, k=3)
            
        tasks = [get_docs(q) for q in questions]
        return await asyncio.gather(*tasks)

    def retrieve(self, state):
        """Retrieve relevant documents based on the question"""
        question = state["question"]
        
        # Generate sub-questions
        questions = self.generate_queries.invoke({
            "question": question,
            "crop": state["crop"]
        })
        
        # Batch retrieve documents
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            retrieved_docs = loop.run_until_complete(self.async_retrieve_docs(questions))
            loop.close()
        except Exception as e:
            print(f"Async retrieval failed, using sync fallback: {e}")
            retrieved_docs = []
            for q in questions:
                docs = self.vectorstore.similarity_search(q, k=3)
                retrieved_docs.append(docs)

        docs = self.get_unique_union(retrieved_docs)
        return {"documents": docs}

    def generate(self, state):
        """Generate response based on retrieved documents"""
        question = state["question"]
        documents = state["documents"]
        
        generation = self.rag_chain.invoke({
            "context": documents,
            "question": question
        })

        groundedness_check = UpstageGroundednessCheck(upstage_api_key=UPSTAGE_API_KEY)
        response = groundedness_check.invoke({
            "context": documents,
            "answer": generation,
        })

        return {
            "documents": documents,
            "question": question,
            "generation": generation,
            "groundedness": response
        }

    def transform_query(self, state):
        """Transform the query for better retrieval"""
        question = state["question"]
        documents = state["documents"]
        better_question = self.question_rewriter.invoke({"question": question})
        return {"documents": documents, "question": better_question}

    def web_search(self, state):
        """Perform web search when vector store retrieval is insufficient"""
        question = state["question"]
        documents = state["documents"]
        
        web_results = self.web_search_tool.invoke({"query": question})
        web_content = "\n".join([d["content"] for d in web_results if isinstance(d, dict)])
        web_doc = Document(page_content=web_content)
        documents.append(web_doc)
        
        return {"documents": documents, "question": question}

    def get_unique_union(self, documents: list[list]):
        """Get unique union of retrieved documents"""
        flattened_docs = [dumps(doc) for sublist in documents for doc in sublist]
        unique_docs = list(set(flattened_docs))
        return [loads(doc) for doc in unique_docs]

    def nothing_retrieved(self, state):
        """Check if any documents were retrieved"""
        return "web_search" if len(state["documents"]) == 0 else "generate"

    def not_grounded(self, state):
        """Check if the response is grounded in the retrieved documents"""
        return state["groundedness"]

    def invoke(self, question, crop):
        """Main entry point for the retrieval graph"""
        os.environ["LANGCHAIN_TRACING_V2"] = "True"
        os.environ["LANGCHAIN_PROJECT"] = "RetrievalGraph"
        return self.app.invoke({"question": question, "crop": crop})["generation"]

if __name__ == "__main__":
    graph = RetrievalGraph()
    response = graph.invoke("""
        You are an agricultural pest management expert is a professional with specialized knowledge in entomology, 
        plant pathology, and crop protection.

        A farmer has come to you with a disease affecting his/her crop. 
        The farmer is growing corn. 
        The farmer has noticed caterpillar insect on the crop.
        His farm's current and next few days weather is sunny.
        His farm's soil moisture is 30. And his irrigation plan is none. 

        You need to provide the farmer with the following information:
        1. Insights on the insect, how it affects the plant and its yield
        2. What factors support insect habitation in your crop field
        3. Now that the insects are present, how to remediate it? Include specific information
            - On what pesticides to use, when to apply given the weather, moisture and irrigation plan
                - explain your reasoning for the timing. Provide reference to the weather and moisture levels and you used it in your reasoning
                - give dates when the pesticides should be applied
            - Where to get the pesticides from
                - Give the websites where the farmer can buy the pesticides
    """, crop="corn")
    print(response)