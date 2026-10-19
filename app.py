
import hashlib
import tempfile
from pathlib import Path

import streamlit as st

from src.pdf_loader import extract_pdf_pages, PDFLoadError
from src.text_splitter import split_pages
from src.vector_store import get_collection, index_chunks
from src.rag_chain import generate_answer, RAGGenerationError


# --------------------------------------------------
# App configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Chat with your PDF",
    page_icon="📄",
    layout="wide",
)

DB_PATH = "chroma_db"


@st.cache_resource
def get_cached_collection(collection_name: str):
    """Reuse a persistent ChromaDB collection."""
    return get_collection(
        db_path=DB_PATH,
        collection_name=collection_name,
    )


# --------------------------------------------------
# Session state
# --------------------------------------------------

if "active_doc_hash" not in st.session_state:
    st.session_state.active_doc_hash = None

if "collection_name" not in st.session_state:
    st.session_state.collection_name = None

if "messages" not in st.session_state:
    st.session_state.messages = []


# --------------------------------------------------
# User interface
# --------------------------------------------------

st.title("📄 Chat with your PDF")
st.caption(
    "Upload a document and ask questions based on its contents."
)

with st.sidebar:
    st.header("Upload document")

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload a text-based PDF to get started.",
    )

    process_button = st.button(
        "Process PDF",
        type="primary",
        disabled=uploaded_file is None,
        use_container_width=True,
    )

    st.divider()

    st.markdown("**Pipeline**")
    st.write("1. Extract PDF text")
    st.write("2. Split text into chunks")
    st.write("3. Generate embeddings")
    st.write("4. Store vectors in ChromaDB")
    st.write("5. Retrieve evidence and generate answers")


# --------------------------------------------------
# PDF ingestion
# --------------------------------------------------

if process_button and uploaded_file is not None:
    pdf_bytes = uploaded_file.getvalue()

    if not pdf_bytes:
        st.error("The uploaded file is empty.")
        st.stop()

    if not pdf_bytes.startswith(b"%PDF-"):
        st.error("The uploaded file does not appear to be a valid PDF.")
        st.stop()

    # Use a content hash to keep different PDFs in separate collections.
    document_hash = hashlib.sha256(pdf_bytes).hexdigest()
    collection_name = f"pdf_{document_hash[:24]}"

    with st.spinner("Extracting text and building the search index..."):
        try:
            # Use a temporary file for the PDF loader.
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf_path = Path(temp_dir) / uploaded_file.name
                pdf_path.write_bytes(pdf_bytes)

                pages = extract_pdf_pages(pdf_path)

            # Replace the temporary filename with the original filename.
            for page in pages:
                page["metadata"]["source"] = uploaded_file.name

            chunks = split_pages(
                pages,
                chunk_size=1000,
                chunk_overlap=200,
            )

            collection = get_cached_collection(collection_name)

            indexed_count = index_chunks(
                chunks,
                collection,
                replace_existing=True,
            )

            # Update session state only after successful indexing.
            if st.session_state.active_doc_hash != document_hash:
                st.session_state.messages = []

            st.session_state.active_doc_hash = document_hash
            st.session_state.collection_name = collection_name

            st.session_state.document_info = {
                "name": uploaded_file.name,
                "pages": len(pages),
                "chunks": indexed_count,
            }

            st.success(
                f"PDF processed successfully: {indexed_count} chunks indexed."
            )

        except PDFLoadError as exc:
            st.error(f"Could not process the PDF: {exc}")

        except ValueError as exc:
            st.error(f"Invalid document content: {exc}")

        except Exception as exc:
            st.error(
                "An unexpected ingestion error occurred. "
                "Check the terminal logs for details."
            )
            print(f"PDF ingestion error: {exc}")


# --------------------------------------------------
# Document status
# --------------------------------------------------

if st.session_state.active_doc_hash:
    info = st.session_state.get("document_info", {})

    st.success(f"Active document: {info.get('name', 'PDF')}")

    col1, col2 = st.columns(2)
    col1.metric("Pages with extracted text", info.get("pages", 0))
    col2.metric("Indexed chunks", info.get("chunks", 0))

    st.divider()

    # Display previous chat messages.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message.get("sources"):
                with st.expander("View source pages"):
                    for source in message["sources"]:
                        st.write(
                            f"- {source['source']}, "
                            f"page {source['page']}"
                        )

    # --------------------------------------------------
    # Chat
    # --------------------------------------------------

    question = st.chat_input("Ask a question about your PDF...")

    if question:
        st.session_state.messages.append(
            {"role": "user", "content": question}
        )

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Searching the document and generating an answer..."):
                try:
                    collection = get_cached_collection(
                        st.session_state.collection_name
                    )

                    result = generate_answer(
                        question=question,
                        collection=collection,
                    )

                    answer = result["answer"]
                    sources = result["sources"]

                    st.markdown(answer)

                    if sources:
                        with st.expander("View source pages"):
                            for source in sources:
                                st.write(
                                    f"- {source['source']}, "
                                    f"page {source['page']}"
                                )

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "sources": sources,
                        }
                    )

                except (RAGGenerationError, ValueError) as exc:
                    error_message = str(exc)
                    st.error(error_message)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": f"Unable to answer: {error_message}",
                        }
                    )

                except Exception as exc:
                    st.error(
                        "An unexpected error occurred while answering. "
                        "Please check the terminal logs."
                    )
                    print(f"Question-answering error: {exc}")

else:
    st.info("Upload a PDF and click **Process PDF** to start chatting.")
