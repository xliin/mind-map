import os, tempfile
import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.text_splitter import TokenTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from PyPDF2 import PdfReader
from langchain.docstore.document import Document
from langchain.callbacks import get_openai_callback

def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] == st.secrets["passwords"]['username'] and st.session_state["password"] == st.secrets["passwords"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store username + password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show inputs for username + password.
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )


        st.error("😕 Usuário ou senha incorreto")
        return False
    else:
        # Password correct.
        return True


if check_password():
    # Streamlit app
    st.subheader('Gerador de Mapa Mental')

    # Set your OpenAI API Key.
    source_doc = st.file_uploader("Escolha seu PDF de um artigo, livro ou texto. Clique em Gerar Mapa Mental e veja a mágica acontecer" , type="pdf")
    # If the 'Summarize' button is clicked
    if st.button("Gerar Mapa Mental"):
        # Validate inputs
        if not source_doc:
            st.error(f"Por favor preencha os campos faltantes.")
        else:
             try:
                with st.spinner('Por favor aguarde...'):
                    # Save uploaded file temporarily to disk, load and split the file into pages, delete temp file
                    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                        tmp_file.write(source_doc.read())
                    loader_mindmap = PdfReader(tmp_file.name)
                    # Store all the text in a variable
                    text = ""
                    for page in loader_mindmap.pages:
                        text += page.extract_text()

                    # Split Data For Mindmap Generation
                    text_splitter = TokenTextSplitter(model_name="gpt-4", chunk_size=10000, chunk_overlap=1000)
                    texts_for_mindmap = text_splitter.split_text(text)
                    docs_for_mindmap = [Document(page_content=t) for t in texts_for_mindmap]

                    # Template for the question generation for every document

                    prompt_template_mindmap = """

                    Você é um assistente experiente em ajudar as pessoas a entender tópicos através da ajuda de mapas mentais.

                    Você é um especialista no campo do tópico solicitado.

                    Faça um mapa mental com base no contexto abaixo. Tente fazer conexões entre os diferentes tópicos e ser conciso.:

                    ------------
                    {text}
                    ------------

                    Pense passo a passo.

                    Responda sempre em texto de marcação. Aderir à seguinte estrutura:

                    ## Tópico Principal 1

                    ### Subtópico 1
                    - Subtópico 1
                        -Subtópico 1
                        -Subtópico 2
                        -Subtópico 3

                    ### Subtópico 2
                    - Subtópico 1
                        -Subtópico 1
                        -Subtópico 2
                        -Subtópico 3

                    ## Tópico Principal 2

                    ### Subtópico 1
                    - Subtópico 1
                        -Subtópico 1
                        -Subtópico 2
                        -Subtópico 3

                    Certifique-se de colocar apenas o texto Markdown, não coloque mais nada. Certifique-se também de que tem o recuo correto e escreva em português brasileiro.

                    MAPA MENTAL EM MARKDOWN:

                    """

                    PROMPT_MINDMAP = PromptTemplate(template=prompt_template_mindmap, input_variables=["text"])

                    # Template for refining the mindmap

                    refine_template_mindmap = ("""

                    Você é um assistente experiente em ajudar as pessoas a entender tópicos através da ajuda de mapas mentais.

                    Você é um especialista no campo do tópico solicitado.

                    Recebemos alguns mapas mentais em markdown até certo ponto: {existing_answer}.
                    Temos a opção de refinar o mapa mental existente ou adicionar novas partes. Tente estabelecer ligações entre os diferentes tópicos e ser conciso.
                    (apenas se necessário) com mais algum contexto abaixo
                    "------------\n"
                    "{text}\n"
                    "------------\n"


                    Responda sempre em texto de marcação. Tente estabelecer ligações entre os diferentes tópicos e ser conciso. Aderir à seguinte estrutura:

                    ## Tópico Principal 1

                    ### Subtópico 1
                    - Subtópico 1
                        -Subtópico 1
                        -Subtópico 2
                        -Subtópico 3

                    ### Subtópico 2
                    - Subtópico 1
                        -Subtópico 1
                        -Subtópico 2
                        -Subtópico 3

                    ## Tópico Principal 2

                    ### Subtópico 1
                    - Subtópico 1
                        -Subtópico 1
                        -Subtópico 2
                        -Subtópico 3



                    Certifique-se de colocar apenas o texto Markdown, não coloque mais nada. Certifique-se também de que tem o recuo correto.

                    MAPA MENTAL EM MARKDOWN:
                    """
                    )
                                                
                    REFINE_PROMPT_MINDMAP = PromptTemplate(
                        input_variables=["existing_answer", "text"],
                        template=refine_template_mindmap,
                    )

                    os.remove(tmp_file.name)
                    # Tracking cost
                    with get_openai_callback() as cb:

                        # Initialize the LLM
                        llm_markdown = ChatOpenAI(model="gpt-4", openai_api_key=API_KEY, temperature=0)

                        # Initialize the summarization chain
                        summarize_chain = load_summarize_chain(llm=llm_markdown, chain_type="refine", verbose=True, question_prompt=PROMPT_MINDMAP, refine_prompt=REFINE_PROMPT_MINDMAP)

                        # Generate mindmap
                        mindmap = summarize_chain(docs_for_mindmap)

                        # Save mindmap to .md file
                        st.markdown(mindmap['output_text'])
                    st.write(cb)
             except Exception as e:
                 st.exception(f"Ocorreu um erro: {e}")

