import re
import os
import json
import glob
import numpy as np
from genai import Client, Credentials
from genai.extensions.langchain import LangChainInterface
from genai.schema import (
    DecodingMethod,
    TextGenerationParameters,
    ModerationHAP,
    ModerationParameters
)
from utils.retriever import ContextRetriever
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from utils import prompts

from langchain_ibm import WatsonxLLM
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

DEFAULT_RESPONSES = [
    f"Hmm.., I'm not sure I have the answer.",
    f"Apologize that I have limited data access in addressing this question.",
    f"Sorry, I can only the questions I have the data on."
]


def watsonx_model(model_id="mistralai/mixtral-8x7b-instruct-v01", decoding_method='greedy', max_new_tokens=600, 
                  min_new_tokens=1, temperature=0.5, top_k=50, top_p=1, repetition_penalty=1):
    params = {
        GenParams.DECODING_METHOD: decoding_method,
        GenParams.MIN_NEW_TOKENS: min_new_tokens,
        GenParams.MAX_NEW_TOKENS: max_new_tokens,
        GenParams.RANDOM_SEED: 42,
        GenParams.TEMPERATURE: temperature,
        GenParams.TOP_K: top_k,
        GenParams.TOP_P: top_p,
        GenParams.REPETITION_PENALTY: repetition_penalty
    }
    ibm_cloud_url = os.getenv("IBM_CLOUD_URL", None)
    project_id = os.getenv("PROJECT_ID", None)
    watsonx_llm = WatsonxLLM(
        model_id=model_id,
        url=ibm_cloud_url,
        project_id=project_id,
        params=params,
    )
    return watsonx_llm

class Processor:
    def __init__(self, llm_config=None):
        if llm_config is None:
            self._llm = watsonx_model()
        else:
            self._llm = watsonx_model(**llm_config)
        self._summary_llm = watsonx_model(model_id="meta-llama/llama-3-8b-instruct")
        self._question_llm = watsonx_model()
        self._flan_llm = watsonx_model(model_id="google/flan-ul2", min_new_tokens=1, max_new_tokens=10)
        self._retriever = ContextRetriever()

    def create_vector_embedding(self):
        all_data = []
        txt_files = glob.glob("data/*.txt")
        for file in txt_files:
            with open(file, "r") as f:
                data_txt = f.read()
            doc_txt = Document(page_content=data_txt.strip(), metadata={"file_path": file})
            all_data.append(doc_txt)

        pdf_files = glob.glob("data/*.pdf") + glob.glob("data/*.PDF")
        for file in pdf_files:
            loader = PyMuPDFLoader(file)
            data_pdf = loader.load()
            pdf_txt = ""
            for doc in data_pdf:
                pdf_txt += (doc.page_content.strip() + "\n")
            doc_pdf = Document(page_content=pdf_txt.strip(), metadata={"file_path": file})
            all_data.append(doc_pdf)

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
        data = text_splitter.split_documents(all_data)
        self._retriever.delete_all_data()
        self._retriever.add_documents(data)

    def add_new_qa(self, question, answer):
        kb_path = "data/knowledge_base.txt"
        if os.path.exists(kb_path):
            with open(kb_path, "r") as f:
                data_txt = f.read()
        else:
            data_txt = ""
        data_txt = data_txt.strip()
        data_txt += "\n\n"
        data_txt += f"-* {question}"
        data_txt += "\n"
        data_txt += answer
        with open(kb_path, "w") as f:
            f.write(data_txt)
        qa = question + "\n" + answer
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000)
        data = text_splitter.create_documents([qa], metadatas=[{"file_path": kb_path}])
        self._retriever.add_documents(data)

    def change_llm_config(self, llm_config):
        self._llm = watsonx_model(**llm_config)
    
    def __prompt_generation(self, context, question, fallback_response):
        template = prompts.QA_prompt_mixtral.format(context=context, question=question, fallback_response=fallback_response)
        return template
    
    def generate_chat_summary(self, question, response, summary=""):
        if summary.strip():
            prompt = prompts.chat_history_summary_prompt.format(summary=summary.strip(), question=question, response=response.strip())
        else:
            prompt = prompts.first_chat_summary_prompt.format(question=question, response=response.strip())
        summary = self._summary_llm.invoke(prompt)
        return summary
    
    def rephrase_question(self, question, summary):
        prompt = prompts.rephrase_question_prompt.format(chat_history=summary, question=question)
        response = self._question_llm.invoke(prompt)
        json_response = """{
"Standalone question": """ + response
        try:
            response_dict = json.loads(json_response)
            rephrased_ques = response_dict["Standalone question"]
        except:
            print("Error in JSON Parsing.")
            re_search = re.search("\".*\"", response)
            if re_search:
                rephrased_ques = re_search.group()[1:-1]
            else:
                rephrased_ques = response
        return rephrased_ques
    
    def get_answer(self, query, num_chunks=2, stream=False):
        docs = self._retriever.get_relevant_docs(query, num_chunks)
        context = "\n\n".join(docs)
        random_int = np.random.randint(len(DEFAULT_RESPONSES))
        fall_back_response = DEFAULT_RESPONSES[random_int]
        prompt = self.__prompt_generation(context, query, fall_back_response)
        if stream:
            answer = self._llm.stream(prompt)
        else:
            answer = self._llm.invoke(prompt)
        return answer, docs
    
    def get_greetings_answer(self, query, stream=False):
        prompt = prompts.greetings_prompt_mixtral.format(query=query)
        if stream:
            answer = self._llm.stream(prompt)
        else:
            answer = self._llm.invoke(prompt)
        return answer, []
    
    def classify_query(self, query):
        prompt = prompts.query_classification_prompt.format(query=query)
        answer = self._flan_llm.invoke(prompt)
        return answer
    
    def respond_to_query(self, orig_query, summary="", num_chunks=2, stream=False, log=False):
        query_class = self.classify_query(orig_query).strip().lower()
        if log:
            print(query_class)
        if query_class=="basic conversational phrases":
            return self.get_greetings_answer(orig_query, stream)
        else:
            if summary:
                query = self.rephrase_question(orig_query, summary)
            else:
                query = orig_query
            if log:
                print("Original Question -", orig_query)
                print("Rephrased Question -", query)
            return self.get_answer(query, num_chunks, stream) 
