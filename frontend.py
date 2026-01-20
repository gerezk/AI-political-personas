import chainlit as cl
from chainlit.input_widget import Select
import ollama

# Initialize the async client
client = ollama.AsyncClient()


@cl.on_chat_start
async def start():
    # avatar files names are the same as agent['name'] in lowercase with space replaced by _:
    # - public/avatars/republican.png
    # - public/avatars/democrat.png

    # Initialize the transcript and settings
    cl.user_session.set("transcript", [])

    settings = await cl.ChatSettings([
        Select(
            id="Persona",
            label="Who should answer?",
            values=["Republican", "Democrat", "Both"],
            initial_index=2
        )
    ]).send()
    cl.user_session.set("settings", settings)

    await cl.Message(content="Welcome to the debate floor! History is being recorded.").send()


@cl.on_message
async def main(message: cl.Message):
    transcript = cl.user_session.get("transcript")
    settings = cl.user_session.get("settings")
    persona_choice = settings.get("Persona")

    # Add user message to history
    transcript.append({"role": "user", "content": message.content})

    agents_to_run = []
    if persona_choice in ["Democrat", "Both"]:
        agents_to_run.append({"name": "Democrat", "model": "dem-model:latest"})
    if persona_choice in ["Republican", "Both"]:
        agents_to_run.append({"name": "Republican", "model": "rep-model:latest"})

    # Sequential execution of models
    for i, agent in enumerate(agents_to_run):
        # The author parameter will automatically use the matching avatar
        # from public/avatars/{author}.png
        agent_msg = cl.Message(content=f"{agent['name']}: ", author=agent["name"])
        await agent_msg.send()

        # If this is NOT the first agent, nudge the model
        current_context = list(transcript)
        if i > 0:
            current_context.append({
                "role": "user",
                "content": message.content,
            })

        print(current_context)
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

            # Update message with final content
            if not full_response:
                agent_msg.content = "*Chose to remain silent.*"
            await agent_msg.update()

            # Save the response to the transcript
            transcript.append({"role": "assistant", "author": agent["name"], "content": full_response})

        except Exception as e:
            await cl.Message(content=f"Error with {agent['name']}: {str(e)}", author="System").send()

    cl.user_session.set("transcript", transcript)


@cl.on_settings_update
async def setup_agent(settings):
    cl.user_session.set("settings", settings)