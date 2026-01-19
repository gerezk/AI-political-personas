import chainlit as cl
from chainlit.input_widget import Select
import ollama

# Initialize the async client
client = ollama.AsyncClient()


@cl.on_chat_start
async def start():
    cl.user_session.set("transcript", [])
    settings = await cl.ChatSettings([
        Select(id="Persona", label="Who should answer?", values=["Republican", "Democrat", "Both"], initial_index=2)
    ]).send()
    cl.user_session.set("settings", settings)
    await cl.Message(content="Welcome to this virtual debate stage! History is being recorded.").send()


@cl.on_message
async def main(message: cl.Message):
    transcript = cl.user_session.get("transcript")
    settings = cl.user_session.get("settings")
    persona_choice = settings.get("Persona")

    # 1. Add user message to history
    transcript.append({"role": "user", "content": message.content})

    agents_to_run = []
    if persona_choice in ["Republican", "Both"]:
        agents_to_run.append({"name": "Republican", "model": "rep-model:latest"})
    if persona_choice in ["Democrat", "Both"]:
        agents_to_run.append({"name": "Democrat", "model": "dem-model:latest"})

    # 2. Sequential execution of models, if "Both" selected
    for i, agent in enumerate(agents_to_run):
        agent_msg = cl.Message(content=f"{agent["name"]}: ", author=agent["name"])
        await agent_msg.send()

        # If this is NOT the first agent, the model needs a "nudge"
        # to know it's their turn after the previous assistant spoke.
        current_context = list(transcript)  # Create a copy
        if i > 0:
            current_context.append({
                "role": "user",
                "content": f"It is now the {agent['name']}'s turn. Please provide your response without any tags."
            })

        full_response = ""
        try:
            stream = await client.chat(
                model=agent["model"],
                messages=current_context,
                stream=True,
                keep_alive=0
            )

            async for chunk in stream:
                token = chunk.get('message', {}).get('content', '')
                if token:
                    full_response += token
                    await agent_msg.stream_token(token)

            # Fix for the Message.update() error
            if not full_response:
                agent_msg.content = f"*{agent['name']} chose to remain silent.*"
                await agent_msg.update()
            else:
                await agent_msg.update()

            # Save the response to the REAL transcript
            transcript.append({"role": "assistant", "content": f"{agent['name']}: {full_response}"})

        except Exception as e:
            await cl.Message(content=f"Error with {agent['name']}: {str(e)}", author="System").send()

    cl.user_session.set("transcript", transcript)

@cl.on_settings_update
async def setup_agent(settings):
    cl.user_session.set("settings", settings)