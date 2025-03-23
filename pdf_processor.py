# pdf_processor.py
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
import time
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

api_key = os.getenv("GOOGLE_API_KEY")

# Read the PDF and return the text
def get_pdf_text(pdf_paths):
    """Extract text from PDF files"""
    text = ""
    for pdf_path in pdf_paths:
        try:
            pdf_reader = PdfReader(pdf_path)
            for page in pdf_reader.pages:
                text += page.extract_text()
        except Exception as e:
            print(f"Error processing {pdf_path}: {str(e)}")
    return text

# Split the text into chunks
def get_text_chunks(text):
    """Split text into manageable chunks"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=10000,
        chunk_overlap=2000,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

# Create vector store from text chunks
def create_vector_store(text_chunks):
    """Convert text chunks to vector embeddings"""
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Create embeddings using Gemini API key
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        
        # Create vectors in smaller batches to avoid timeout
        
        # this will store embeddings or you can say, FAISS index of embeddings.
        vector_store = None

        # text will be processed in batches of 10 to prevent API timeouts
        batch_size = 10
        

        # iterate over text chunks in batches
        # each iteration processes a batch of 10 text chunks
        for i in range(0, len(text_chunks), batch_size):
            batch = text_chunks[i:i+batch_size]
            
            if vector_store is None:
                vector_store = FAISS.from_texts(batch, embedding=embeddings)
            else:
                batch_store = FAISS.from_texts(batch, embedding=embeddings)
                vector_store.merge_from(batch_store)
            
            # Add a small delay to avoid rate limiting
            time.sleep(1)
        
        # Save the vector store
        # Storing it locally instead of some Database
        os.makedirs("vector_store", exist_ok=True)
        vector_store.save_local("vector_store/faiss_index")
        return True
    except Exception as e:
        print(f"Error creating vector store: {str(e)}")
        return False

# Process PDFs and update status
def process_pdfs(pdf_paths, status_dict):
    """Process PDFs and create vector store"""
    try:
        # Extract text from PDFs
        status_dict["message"] = "Extracting text from PDFs..."
        raw_text = get_pdf_text(pdf_paths)
        
        if not raw_text:
            status_dict["status"] = "failed"
            status_dict["message"] = "Could not extract text from PDFs."
            return
        
        # Create text chunks
        status_dict["message"] = "Creating text chunks..."
        text_chunks = get_text_chunks(raw_text)
        
        # Create vector store
        status_dict["message"] = f"Creating vector embeddings for {len(text_chunks)} chunks..."
        success = create_vector_store(text_chunks)
        
        if success:
            status_dict["status"] = "completed"
            status_dict["message"] = "PDF processing completed successfully."
        else:
            status_dict["status"] = "failed"
            status_dict["message"] = "Failed to create vector store."
            
    except Exception as e:
        status_dict["status"] = "failed"
        status_dict["message"] = f"Error processing PDFs: {str(e)}"

# Create Q&A chain
def get_conversational_chain():
    """Create LLM chain for question answering"""
    # Configure the Gemini API
    genai.configure(api_key=api_key)
    
    # Prompt template for Q&A
    prompt_template = """
If the answer is found in the provided context, answer it with all available details.
If the answer is NOT in the provided context, start with:

"⚠️ The question is not related to the uploaded PDF, but here's the response:"

Then proceed to answer the question normally, even if it's outside the context.

Context:
{context}

Question:
{question}

Answer:
"""
    
    # Create LLM model
    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",  # Use gemini-pro model
        temperature=0.3,
        google_api_key=api_key
    )
    
    # Create prompt
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    
    # Create chain
    chain = load_qa_chain(llm=model, chain_type="stuff", prompt=prompt)
    
    return chain

# Get answer from PDFs
def get_answer_from_pdfs(question):
    """Get answer for a question from processed PDFs"""
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Create embeddings
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        
        # Load vector store
        if not os.path.exists("vector_store/faiss_index"):
            return "No processed documents found. Please upload PDFs first."
        
        vector_store = FAISS.load_local("vector_store/faiss_index", embeddings, allow_dangerous_deserialization=True)
        
        # Perform similarity search
        # Retrieval functionality of RAG basically...
        docs = vector_store.similarity_search(question)
        
        # Get chain
        chain = get_conversational_chain()
        
        # Get response
        response = chain(
            {"input_documents": docs, "question": question},
            return_only_outputs=True
        )
        
        return response["output_text"]
    except Exception as e:
        print(f"Error getting answer: {str(e)}")
        raise Exception(f"Error processing question: {str(e)}")