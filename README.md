# llamka

Chatbot ecosystem: grow your second brain here

Framework/API/UI to develop/educate/evaluate and compare your chatbots

## Architecture

* llore - (llamka-core) Tornado App that keep everything running. llore provides api and all other services built on top of it
    * provide absration interface over LLM providers (local, remote)
    * maintain chatbot library (includes: system prompt, finetuning and augmentation pipelines, data dependencies, and build schedule)
    * stores chatbot interactions in oumi conversation format per user
    * maintain libraries of conversation datasets and use them for tuning
    * maintain external document locations and rebuild vector db collections on changes
    * schedule and run pipelines: finetuning, RAG, chatbot evaluation 
    * monitor and run services: databases, queues, proxies, ui (llit)

* llit - streamlit UI 
    * Chatbot interaction, Inspect previous conversations or from library
    * Inspect data: sql, document db, vector db
    * Inspect logs from pipelines
    * Configuration: models, chatbot, pipelines




 ## Unsorted thoughts

* Pipeline that run periodically and retrieve documents from varies sources
* Cut documents in chunks and store them in *croma vector db* adding metedata that points back to original documents
* Run queries from ChatBot thru RAG pipeline that use vector db above


* * *

## Project Docs

For how to install uv and Python, see [installation.md](installation.md).

For development workflows, see [development.md](development.md).

For instructions on publishing to PyPI, see [publishing.md](publishing.md).

* * *

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
