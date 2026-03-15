from google import genai

client = genai.Client(api_key="AIzaSyDZrvzHwoakTjT2Td9bqavzdJ5toXKmh9w")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="say hello"
)

print(response.text)