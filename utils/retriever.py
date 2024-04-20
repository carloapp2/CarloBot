from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

class ContextRetriever:
    def __init__(self, embedding_modelname = "mixedbread-ai/mxbai-embed-large-v1"):
        print("Loading Embedding Model")
        model_kwargs = {'device': 'cpu'}
        embeddings_model = HuggingFaceEmbeddings(
            model_name=embedding_modelname,
            model_kwargs=model_kwargs
        )
        print("Creating Vector Database")
        self._db  = Chroma(collection_name="data", embedding_function=embeddings_model)
        print("Completed Creating Vector DB")

    def __delete_existing_data(self, db):
        ids = db.get()['ids']
        if ids:
            db.delete(ids=ids)

    def delete_all_data(self):
        self.__delete_existing_data(self._db)
    
    def add_documents(self, data):
        print("Adding Documents to Vector Database")
        self._db.add_documents(data)
        print("Completed adding Documents to Vector Database")
    
    def get_relevant_docs(self, query, num_chunks=4):
        relevant_docs = self._db.similarity_search(query, k=num_chunks)
        docs = [doc.page_content for doc in relevant_docs]
        return docs