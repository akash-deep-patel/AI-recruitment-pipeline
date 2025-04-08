import matplotlib.pyplot as plt
import requests
import json
import time
import streamlit as st
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain_core.documents import Document
from langchain_groq import ChatGroq
import os
import pandas as pd
load_dotenv()
# Streamlit app
st.title("Analyze Profile")
# File upload
uploaded_file = st.file_uploader("Upload a PDF or DOCX file", type=["pdf", "docx"])
model = ChatGroq(model="llama3-8b-8192", temperature=0.0)
## Analyze button
if st.button("Analyze"):
    if uploaded_file is not None:
        # Process the uploaded file
        if uploaded_file.type == "application/pdf":
            with open(uploaded_file.name, "wb") as temp_file:
                temp_file.write(uploaded_file.getbuffer())
            loader = PyPDFLoader(uploaded_file.name)
            # Load documents
            doc = loader.load()
            doc_page_contents = [" ".join(page.page_content.splitlines()) for page in doc]
            doc_content = " ".join(doc_page_contents)
            doc = Document(metadata={"source": uploaded_file.name}, page_content=doc_content)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or uploaded_file.name.endswith(".docx"):
            with open(uploaded_file.name, "wb") as temp_file:
                temp_file.write(uploaded_file.getbuffer())
            loader = Docx2txtLoader(uploaded_file.name)
            doc = loader.load()[0]

        else:
            st.error("Unsupported file type!")
            st.stop()
        st.success("File processed successfully!")

        # Display document content
        # for i, d in enumerate(doc):
        st.subheader(f"Document 1: {doc.metadata['source']}")
        # st.write(doc.page_content)

        context = doc.page_content
        messages = [("system", f"You are a helpful assistant with capability of answering a question from this context {context}."),  
        ("human", "extract following info from the context and output in json format: name, email, phone, college, experience. Experience has companies worked for, duration along with the skills used"),]
        print("invoking model")
        ai_msg=model.invoke(messages)
        st.write(ai_msg.content)
        
        messages = [("system", f"You are a helpful assistant with capability of answering a question from this context {context}."),  
        ("human", "list out the company names the person has worked for along with the duration served in number of months with no preamble. If start month is not available take last working month of previous company as start month on next company based on calendar months."),]
        print("invoking model")
        ai_msg=model.invoke(messages)
        print(ai_msg.content)
        for i, line in enumerate(ai_msg.content.split("\n")):
            if i == 0:
                st.write("Company names and months served")
            st.write(line)
        companies = [line.split("-")[0].split(".")[1].strip() for line in ai_msg.content.split("\n") if line.strip() and line.split("-")[0].split(".")[0] != line]
        durations = [line.split("-")[1].strip().split(" ")[0].strip() for line in ai_msg.content.split("\n") if line.strip() and line.split("-")[0].split(".")[0] != line]
        # Draw a plot for companies and respective durations and render to Streamlit UI
        # Convert durations to integers
        durations = [int(duration) for duration in durations]

        # Create a bar plot
        plt.figure(figsize=(10, 6))
        plt.bar(companies, durations, color='skyblue')
        plt.xlabel('Companies')
        plt.ylabel('Duration (Months)')
        plt.title('Duration Served at Each Company')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Render the plot in Streamlit
        st.pyplot(plt)


        #find out company_types "Service", "Product", "start-up", "R&D", "GCC"
        url = "https://google.serper.dev/search"
        # companies = ['Cognizant', 'TCS', 'Infosys', 'Wipro', 'Accenture']
        companies_type_sents = []
        companies_type = [] # list containing the type of companies: product or service based
        for i,company in enumerate(companies):

            payload = json.dumps({
                "q": f"{company} company type",
            })
            headers = {
                'X-API-KEY': 'b7b560827bca711a1a8918e64d023fe353a30c4d',
                'Content-Type': 'application/json'
            }
            if i !=0 and i % 3 == 0:
                # response = requests.request("POST", url, headers=headers, data=payload)
                time.sleep(50)
            response_serper = requests.request("POST", url, headers=headers, data=payload)
            print(response_serper.text)
            # print("invoking model for text",response.text)
            COMPANY_TYPES = ["Service", "Product", "start-up", "R&D", "GCC"]

            response = model.invoke([("system", f"tag the company in mentioned user message with one of the labels from {COMPANY_TYPES} along with the confidence score referring to this text : {response_serper.text} with no explanation in format of <label> <confidence_score>"),
                                    ("human", f"{company}")])
            print(response.content)
            companies_type_sents.append(response.content)
        #enclose for loop with try except to handle the errors
        # Display the company types and confidence scores
        st.subheader("Company Types and Confidence Scores")
        # Display the company types and confidence scores in a table format
        try:
            for i, line in enumerate(companies_type_sents):
                if i == 0:
                    st.write("Company, Company types and confidence scores")
                data = {
                    "Company": companies,
                    "Type": [line.split(" ")[0].strip() for line in companies_type_sents],
                    "Confidence Score": [line.split(" ")[1].strip() for line in companies_type_sents]
                }
                df = pd.DataFrame(data)
                st.table(df)
        except Exception as e:
            st.error(f"An error occurred while processing company types: {e}")
        
        #display the experience in a table format in various company types
        experience_company_types = [0]*len(COMPANY_TYPES)
        for i, company in enumerate(companies):
            for j, company_type in enumerate(COMPANY_TYPES):
                if companies_type_sents[i].split(" ")[0].strip() == company_type:
                    experience_company_types[j] += durations[i]
        # Create a bar chart for experience in different company types
        plt.figure(figsize=(10, 6))
        plt.bar(COMPANY_TYPES, experience_company_types, color='skyblue')
        plt.xlabel('Company Types')
        plt.ylabel('Experience (Months)')
        plt.title('Experience Distribution by Company Type')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        # Render the plot in Streamlit
        st.pyplot(plt)
        
    else:
        st.error("Please upload a file before analyzing.")