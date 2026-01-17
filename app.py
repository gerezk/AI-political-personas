import chainlit as cl
from chainlit.input_widget import Select
import ollama

# Ensure the client is initialized
client = ollama.AsyncClient()


@cl.on_chat_start
async def start():
    cl.user_session.set("transcript", [])
    settings = await cl.ChatSettings([
        Select(id="Persona", label="Who should answer?", values=["Democrat", "Republican", "Both"], initial_index=2)
    ]).send()
    cl.user_session.set("settings", settings)
    await cl.Message(content="Welcome to the Debate Hub! History is being recorded.").send()


@cl.on_message
async def main(message: cl.Message):
    transcript = cl.user_session.get("transcript")
    settings = cl.user_session.get("settings")
    persona_choice = settings.get("Persona")

    # 1. Add the user's message to history
    transcript.append({"role": "user", "content": message.content})

    agents_to_run = []
    if persona_choice in ["Republican", "Both"]:
        agents_to_run.append({"name": "Republican", "model": "rep-model:latest",
                              "prompt": "You are a staunch Republican. Defend your view based on this history: "})

    if persona_choice in ["Democrat", "Both"]:
        agents_to_run.append({"name": "Democrat", "model": "dem-model:latest",
                              "prompt": "You are a passionate Democrat. Defend your view based on this history: "})

    # 2. Run agents sequentially (RAM safety)
    for agent in agents_to_run:
        # Initialize the message in the UI
        agent_msg = cl.Message(content=f"{agent["name"]}: ", author=agent["name"])
        await agent_msg.send()

        # CORRECTED: Create a list where the system prompt is the first element,
        # then "spread" the transcript list into it.
        full_context = [
                           {"role": "system", "content": agent["prompt"]}
                       ] + transcript

        full_response = ""
        try:
            stream = await client.chat(
                model=agent["model"],
                messages=full_context,
                stream=True
            )

            async for chunk in stream:
                if token := chunk['message']['content']:
                    full_response += token
                    await agent_msg.stream_token(token)

            await agent_msg.update()

            # 3. Save the response to history so the NEXT agent sees it
            # We prefix it with the name so the LLM understands who is speaking
            transcript.append({"role": "assistant", "content": f"{agent['name']}: {full_response}"})

        except Exception as e:
            await cl.Message(content=f"Error with {agent['name']}: {str(e)}", author="System").send()

    # 4. Save updated transcript back to the session
    cl.user_session.set("transcript", transcript)


@cl.on_settings_update
async def setup_agent(settings):
    cl.user_session.set("settings", settings)