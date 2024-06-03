import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader, PyMuPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

# Instantiate the Embedding Model
embed_model = FastEmbedEmbeddings(model_name="BAAI/bge-base-en-v1.5")

# Function to load documents from the "upload" folder
def load_local_documents(folder_path):
    docs = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if filename.endswith(".pdf"):
            loader = PyMuPDFLoader(file_path)
            docs.extend(loader.load())
        elif filename.endswith(".txt"):
            loader = TextLoader(file_path)
            docs.extend(loader.load())
    return docs

# Function to download and process documents
def process_documents(urls, folder_path):
    docs = []
    for url in urls:
        try:
            docs.append(WebBaseLoader(url).load())
        except Exception as e:
            print(f"Error loading {url}: {e}")
    docs_list = [item for sublist in docs for item in sublist]
    
    # Load local documents from the "upload" folder
    local_docs = load_local_documents(folder_path)
    docs_list.extend(local_docs)
    
    return docs_list

# Function to chunk documents
def chunk_documents(docs_list):
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=512, chunk_overlap=0
    )
    doc_splits = text_splitter.split_documents(docs_list)
    return doc_splits

# Function to load documents into vectorstore
def load_to_vectorstore(doc_splits):
    try:
        vectorstore = Chroma.from_documents(documents=doc_splits,
                                            embedding=embed_model,
                                            collection_name="local-rag")
        return vectorstore
    except Exception as e:
        print(f"Error loading documents into vectorstore: {e}")
        return None

# Function to instantiate the retriever
def get_retriever(vectorstore):
    try:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
        return retriever
    except Exception as e:
        print(f"Error creating retriever: {e}")
        return None

# Main function to handle embedding process
def setup_embedding(urls, folder_path):
    docs_list = process_documents(urls, folder_path)
    if not docs_list:
        print("No documents were loaded.")
        return None
    doc_splits = chunk_documents(docs_list)
    vectorstore = load_to_vectorstore(doc_splits)
    if not vectorstore:
        print("Vectorstore creation failed.")
        return None
    retriever = get_retriever(vectorstore)
    if not retriever:
        print("Retriever creation failed.")
    return retriever
