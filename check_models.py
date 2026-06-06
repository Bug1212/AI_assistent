from groq import Groq
import config

client = Groq(api_key=config.GROQ_API_KEY)
models = client.models.list()
for m in models.data:
    print(m.id)
