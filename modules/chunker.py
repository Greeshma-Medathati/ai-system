import tiktoken

MAX_TOKENS = 3000

def chunk_text(text: str, model="gpt-4.1-mini"):
    """
    Splits long text into chunks that fit safely within model token limits.
    """
    encoding = tiktoken.encoding_for_model(model)

    tokens = encoding.encode(text)

    chunks = []
    for i in range(0, len(tokens), MAX_TOKENS):
        chunk_tokens = tokens[i:i + MAX_TOKENS]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)

    return chunks