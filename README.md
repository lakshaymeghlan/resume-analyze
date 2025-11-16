the project is fully functional. Anyone can clone the repository and run it locally by supplying their own API key from any LLM provider.

Simply set the following environment variables:

LLM_API_KEY=your_api_key
LLM_PROVIDER=openai / deepseek / anthropic / gemini / groq


Then run:

Backend

pip install -r requirements.txt
uvicorn main:app --reload


Frontend

npm install
npm run dev
